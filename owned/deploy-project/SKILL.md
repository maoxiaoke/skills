---
name: deploy-project
description: Deploy project to Vercel with GitHub and automated DNS setup
---

# Complete Deployment Process

This skill provides smart deployment workflows:

**First Deployment:**
1. Create GitHub repository
2. Deploy to Vercel
3. Set up custom DNS on Cloudflare (automated)

**Subsequent Deployments (Auto-detected):**
1. Commit and push code changes
2. Deploy to Vercel

The script automatically detects if setup is already complete and skips unnecessary steps.

## Prerequisites

Required CLI tools:
- `gh` (GitHub CLI) - for repository creation
- `vercel` (Vercel CLI) - for deployment
- `node` - for DNS automation script

**Authentication Setup:**

1. **GitHub CLI:**
   ```bash
   gh auth login
   ```

2. **Vercel CLI:**
   ```bash
   vercel login
   ```

3. **Cloudflare API Token:**
   - Visit: https://dash.cloudflare.com/profile/api-tokens
   - Click "Create Token"
   - Use "Edit zone DNS" template
   - Select your domain under Zone Resources
   - Export the token:
     ```bash
     export CLOUDFLARE_DNS_API_TOKEN="your-token-here"
     ```

## Step 1: Initialize Git Repository

```bash
# Check if already a git repo
git status

# If not, initialize
git init

# Create .gitignore for Next.js
cat > .gitignore << 'EOF'
# dependencies
/node_modules
/.pnp
.pnp.js

# testing
/coverage
/playwright-report
/test-results

# next.js
/.next/
/out/

# production
/build

# misc
.DS_Store
*.pem

# debug
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# local env files
.env*.local
.env

# vercel
.vercel

# typescript
*.tsbuildinfo
next-env.d.ts
EOF

# Initial commit
git add .
git commit -m "Initial commit

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

## Step 2: Create GitHub Repository

```bash
# Check GitHub authentication
gh auth status

# Create repository and push
gh repo create {project-name} --public --source=. --remote=origin --description="{description}"
git push -u origin main
```

If not authenticated, run `gh auth login` first.

## Step 3: Deploy to Vercel

```bash
# Check Vercel authentication
vercel whoami

# Deploy to production
vercel --yes --prod
```

If not authenticated, run `vercel login` first.

**Expected Output:**
```
Production: https://{project}-xxx.vercel.app
Aliased: https://{project}.vercel.app
```

## Step 4: Set Up Custom Domain (Automated)

### 4a. Add Domain to Vercel and Extract CNAME Target

```bash
# Add custom domain to Vercel project
vercel domains add {project}.nazha.co
```

**Vercel will output the recommended DNS configuration.**

Example output:
```
> Success! Domain {project}.nazha.co added to project {project}.
WARN! This domain is not configured properly. To configure it you should either:
  a) Set the following record on your DNS provider to continue:
     `CNAME {project}.nazha.co 9931e99872af7dfe.vercel-dns-017.com` [recommended]
```

**Important:** Vercel generates a **project-specific CNAME target** (e.g., `9931e99872af7dfe.vercel-dns-017.com`). This is better than the generic `cname.vercel-dns.com`.

### 4a-1. Extract CNAME Target Automatically (Optional)

To automatically extract the CNAME target from Vercel's output:

```bash
# Method 1: Parse the output
CNAME_TARGET=$(vercel domains add {project}.nazha.co 2>&1 | grep -oE '[a-f0-9]+\.vercel-dns-[0-9]+\.com' | head -1)

# Method 2: Check if already added, view in Vercel dashboard
# If domain already exists, visit:
# https://vercel.com/[your-account]/[project]/settings/domains
# Click on the domain to see the recommended CNAME

echo "CNAME target: $CNAME_TARGET"
```

If extraction fails or domain already exists:
1. Visit Vercel dashboard → Project → Settings → Domains
2. Click on your domain to see "DNS Change Recommended"
3. Copy the CNAME target value (e.g., `9931e99872af7dfe.vercel-dns-017.com`)

### 4b. Create DNS Record (Automated with Script)

**First, export your Cloudflare API token:**

```bash
export CLOUDFLARE_DNS_API_TOKEN="your-cloudflare-api-token"
```

**How to get Cloudflare API Token:**
1. Visit https://dash.cloudflare.com/profile/api-tokens
2. Click "Create Token"
3. Use "Edit zone DNS" template
4. Select your domain under Zone Resources
5. Click "Continue to summary" → "Create Token"
6. Copy the token and export it as shown above

**Run the DNS setup script:**

```bash
# Use the CNAME target from Vercel (either extracted or copied from dashboard)
node ~/.claude/skills/deploy-project/setup-cloudflare-dns.js \
  {project} \
  nazha.co \
  9931e99872af7dfe.vercel-dns-017.com

# Or use the variable if you extracted it automatically
node ~/.claude/skills/deploy-project/setup-cloudflare-dns.js \
  {project} \
  nazha.co \
  "$CNAME_TARGET"
```

**Note:** Replace `9931e99872af7dfe.vercel-dns-017.com` with the actual CNAME target from your Vercel output.

**Script Features:**
- ✅ Validates inputs and authentication
- ✅ Checks for existing DNS records
- ✅ Prevents accidental overwrites
- ✅ Shows clear success/error messages

**Expected Output:**
```
🌐 Cloudflare DNS Setup
✓ Zone ID: xxx...
✓ No existing record found
📝 Creating CNAME record...
✅ DNS record created successfully!

🌐 Your domain: https://{project}.nazha.co
⏱️  DNS propagation may take 2-5 minutes
```

### 4c. Verify DNS Setup

```bash
# Check DNS propagation
dig {project}.nazha.co CNAME +short

# Test HTTPS access
curl -I https://{project}.nazha.co
```

Expected: `HTTP/2 200` with `server: Vercel`

## Manual DNS Setup (Fallback)

If automated script fails, you can set up DNS manually:

1. Login to Cloudflare Dashboard at https://dash.cloudflare.com/login
2. Select your domain (e.g., `nazha.co`)
3. Go to DNS → Records
4. Click "Add record"
5. Fill in:
   - Type: CNAME
   - Name: {project}
   - Target: Use the CNAME target from Vercel (e.g., `9931e99872af7dfe.vercel-dns-017.com`)
   - Proxy status: DNS only (grey cloud)
6. Click "Save"

**Important:** Always use the **project-specific CNAME target** shown in your Vercel dashboard, not the generic `cname.vercel-dns.com`.

## Verification Checklist

After deployment, verify:

- [ ] GitHub repository created and code pushed
- [ ] Vercel deployment successful (green status)
- [ ] Production URL accessible (https://{project}.vercel.app)
- [ ] Custom domain added to Vercel
- [ ] DNS CNAME record created in Cloudflare
- [ ] Custom domain accessible (https://{project}.nazha.co)
- [ ] SSL certificate issued (https works)

## Common Issues & Solutions

### Issue: "gh: command not found"
**Solution:** Install GitHub CLI
```bash
brew install gh
gh auth login
```

### Issue: "vercel: command not found"
**Solution:** Install Vercel CLI
```bash
npm install -g vercel
vercel login
```

### Issue: "CLOUDFLARE_DNS_API_TOKEN not set"
**Solution:** Get your API token from Cloudflare and export it
```bash
# Get token from: https://dash.cloudflare.com/profile/api-tokens
export CLOUDFLARE_DNS_API_TOKEN="your-cloudflare-api-token"
```

For permanent setup, add to `~/.zshrc` or `~/.bashrc`:
```bash
echo 'export CLOUDFLARE_DNS_API_TOKEN="your-token"' >> ~/.zshrc
source ~/.zshrc
```

### Issue: "Domain not found in Cloudflare"
**Solution:** Verify domain is added to your Cloudflare account

### Issue: DNS not propagating
**Wait:** DNS propagation takes 2-5 minutes typically
**Check:** Use https://dnschecker.org to verify global propagation

## Smart Deployment Script

The deployment script automatically detects if this is a first deployment or redeployment:

### First Deployment (Full Setup)
```bash
# Runs all steps: Git → GitHub → Vercel → Domain → DNS
~/.claude/skills/deploy-project/deploy.sh myproject "My app"
```

### Redeployment (Quick Mode - Auto-detected)
```bash
# Only: Commit → Push → Deploy
# Automatically skips GitHub/DNS setup if already configured
~/.claude/skills/deploy-project/deploy.sh myproject
```

### Force Full Setup
```bash
# Use --full flag to reconfigure everything
~/.claude/skills/deploy-project/deploy.sh myproject "My app" --full
```

**How it works:**
- Detects existing git repository with matching remote
- Skips GitHub repo creation if already exists
- Skips DNS setup if already configured
- Always commits changes and deploys to Vercel
- Provides clear feedback about what it's doing

## DNS Script Usage

The `setup-cloudflare-dns.js` script can be used for any project:

```bash
# Basic usage
node setup-cloudflare-dns.js <subdomain> <domain> <target>

# With Cloudflare proxy
node setup-cloudflare-dns.js app nazha.co target.com --proxied

# Update existing record
node setup-cloudflare-dns.js app nazha.co new-target.com --force
```

## API Token Management

**Cloudflare API Token Setup:**

1. **Create Token:**
   - Visit: https://dash.cloudflare.com/profile/api-tokens
   - Click "Create Token"
   - Use "Edit zone DNS" template
   - Select your domain under Zone Resources
   - Save the token securely

2. **Required Permissions:**
   - Zone.DNS - Edit
   - Zone.Zone - Read (optional)

3. **Export Token:**
   ```bash
   export CLOUDFLARE_DNS_API_TOKEN="your-token-here"
   ```

4. **Permanent Setup:**
   Add to `~/.zshrc` or `~/.bashrc`:
   ```bash
   echo 'export CLOUDFLARE_DNS_API_TOKEN="your-token"' >> ~/.zshrc
   source ~/.zshrc
   ```

**Security Best Practices:**
- Never commit tokens to git
- Store in environment variables only
- Rotate tokens periodically
- Use project-specific tokens when possible
- Never share tokens publicly

## Resources

- GitHub CLI: https://cli.github.com
- Vercel CLI: https://vercel.com/docs/cli
- Cloudflare API: https://developers.cloudflare.com/api/
- DNS Checker: https://dnschecker.org
