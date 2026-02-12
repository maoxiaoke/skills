#!/usr/bin/env node

/**
 * Cloudflare DNS Record Setup Script
 *
 * Creates a CNAME record in Cloudflare for a subdomain pointing to a target.
 * Commonly used for setting up custom domains for Vercel deployments.
 *
 * Usage:
 *   node setup-cloudflare-dns.js <subdomain> <domain> <target> [--proxied]
 *
 * Example:
 *   node setup-cloudflare-dns.js beauties nazha.co cname.vercel-dns.com
 *
 * Environment Variables:
 *   CLOUDFLARE_DNS_API_TOKEN - Your Cloudflare API token (required)
 *
 * To create an API token:
 *   1. Go to https://dash.cloudflare.com/profile/api-tokens
 *   2. Click "Create Token"
 *   3. Use "Edit zone DNS" template
 *   4. Select your domain under Zone Resources
 *   5. Create and copy the token
 */

const https = require('https');

// Parse command line arguments
const args = process.argv.slice(2);
const [subdomain, domain, target] = args;
const proxied = args.includes('--proxied');

// Validate inputs
if (!subdomain || !domain || !target) {
  console.error('❌ Error: Missing required arguments\n');
  console.log('Usage: node setup-cloudflare-dns.js <subdomain> <domain> <target> [--proxied]');
  console.log('\nExample:');
  console.log('  node setup-cloudflare-dns.js beauties nazha.co cname.vercel-dns.com');
  console.log('\nOptions:');
  console.log('  --proxied    Enable Cloudflare proxy (orange cloud)');
  console.log('\nEnvironment:');
  console.log('  CLOUDFLARE_DNS_API_TOKEN must be set');
  process.exit(1);
}

const apiToken = process.env.CLOUDFLARE_DNS_API_TOKEN;
if (!apiToken) {
  console.error('❌ Error: CLOUDFLARE_DNS_API_TOKEN environment variable is not set');
  console.log('\nTo get your API token:');
  console.log('  1. Visit https://dash.cloudflare.com/profile/api-tokens');
  console.log('  2. Create a token with "Edit zone DNS" permissions');
  console.log('  3. Export it: export CLOUDFLARE_DNS_API_TOKEN="your-token"');
  process.exit(1);
}

/**
 * Make an HTTPS request to Cloudflare API
 */
function cloudflareRequest(method, path, data = null) {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: 'api.cloudflare.com',
      port: 443,
      path: `/client/v4${path}`,
      method: method,
      headers: {
        'Authorization': `Bearer ${apiToken}`,
        'Content-Type': 'application/json'
      }
    };

    const req = https.request(options, (res) => {
      let body = '';
      res.on('data', (chunk) => body += chunk);
      res.on('end', () => {
        try {
          const json = JSON.parse(body);
          if (json.success) {
            resolve(json);
          } else {
            reject(new Error(json.errors?.[0]?.message || 'API request failed'));
          }
        } catch (error) {
          reject(new Error(`Failed to parse response: ${error.message}`));
        }
      });
    });

    req.on('error', reject);

    if (data) {
      req.write(JSON.stringify(data));
    }

    req.end();
  });
}

/**
 * Get Zone ID for a domain
 */
async function getZoneId(domain) {
  console.log(`🔍 Looking up Zone ID for ${domain}...`);

  const response = await cloudflareRequest('GET', `/zones?name=${domain}`);

  if (!response.result || response.result.length === 0) {
    throw new Error(`Domain ${domain} not found in your Cloudflare account`);
  }

  const zoneId = response.result[0].id;
  console.log(`✓ Zone ID: ${zoneId}`);
  return zoneId;
}

/**
 * Check if DNS record already exists
 */
async function checkExistingRecord(zoneId, recordName) {
  console.log(`\n🔍 Checking for existing DNS record...`);

  try {
    const response = await cloudflareRequest('GET', `/zones/${zoneId}/dns_records?name=${recordName}`);

    if (response.result && response.result.length > 0) {
      const existing = response.result[0];
      console.log(`⚠️  Found existing ${existing.type} record:`);
      console.log(`   ${existing.name} → ${existing.content}`);
      console.log(`   Proxied: ${existing.proxied ? 'Yes' : 'No'}`);
      return existing;
    }

    console.log(`✓ No existing record found`);
    return null;
  } catch (error) {
    console.log(`✓ No existing record found`);
    return null;
  }
}

/**
 * Create CNAME DNS record
 */
async function createDnsRecord(zoneId, recordName, target, proxied) {
  console.log(`\n📝 Creating CNAME record...`);
  console.log(`   Name: ${recordName}`);
  console.log(`   Target: ${target}`);
  console.log(`   Proxied: ${proxied ? 'Yes (orange cloud)' : 'No (DNS only)'}`);

  const data = {
    type: 'CNAME',
    name: subdomain,
    content: target,
    ttl: 1, // Auto
    proxied: proxied
  };

  await cloudflareRequest('POST', `/zones/${zoneId}/dns_records`, data);
  console.log(`✅ DNS record created successfully!`);
}

/**
 * Update existing DNS record
 */
async function updateDnsRecord(zoneId, recordId, target, proxied) {
  console.log(`\n📝 Updating existing DNS record...`);

  const data = {
    type: 'CNAME',
    name: subdomain,
    content: target,
    ttl: 1,
    proxied: proxied
  };

  await cloudflareRequest('PUT', `/zones/${zoneId}/dns_records/${recordId}`, data);
  console.log(`✅ DNS record updated successfully!`);
}

/**
 * Main execution
 */
async function main() {
  console.log('🌐 Cloudflare DNS Setup\n');
  console.log(`Setting up: ${subdomain}.${domain} → ${target}\n`);

  try {
    // Get Zone ID
    const zoneId = await getZoneId(domain);

    // Check for existing record
    const recordName = `${subdomain}.${domain}`;
    const existing = await checkExistingRecord(zoneId, recordName);

    if (existing) {
      // Ask if we should update
      console.log(`\n⚠️  Record already exists. Do you want to update it?`);
      console.log(`   Current: ${existing.content}`);
      console.log(`   New: ${target}`);
      console.log(`\n   To update, run again with --force flag`);

      if (args.includes('--force')) {
        await updateDnsRecord(zoneId, existing.id, target, proxied);
      } else {
        console.log(`\n   Skipping update. Use --force to update.`);
        process.exit(0);
      }
    } else {
      // Create new record
      await createDnsRecord(zoneId, recordName, target, proxied);
    }

    // Success summary
    console.log(`\n${'═'.repeat(60)}`);
    console.log(`✅ Setup Complete!`);
    console.log(`${'═'.repeat(60)}`);
    console.log(`\n🌐 Your domain: https://${recordName}`);
    console.log(`📍 Points to: ${target}`);
    console.log(`⚡ Proxy: ${proxied ? 'Enabled' : 'Disabled'}`);
    console.log(`\n⏱️  DNS propagation may take 2-5 minutes`);
    console.log(`\nVerify with: dig ${recordName} CNAME +short`);

  } catch (error) {
    console.error(`\n❌ Error: ${error.message}`);
    process.exit(1);
  }
}

// Run the script
main();
