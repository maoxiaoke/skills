# Deploy Project Skill

Complete deployment workflow for Vercel projects with automated DNS setup.

## What This Skill Does

1. ✅ Creates GitHub repository
2. ✅ Deploys to Vercel (production)
3. ✅ Sets up custom domain on nazha.co
4. ✅ Configures DNS automatically via Cloudflare API

## Files Included

- `SKILL.md` - Complete deployment instructions
- `setup-cloudflare-dns.js` - Automated DNS configuration script
- `README.md` - This file

## Quick Start

### Option 1: Use the Skill (Recommended)

In Claude Code, simply say:
```
/deploy-project
```

Claude will follow the complete deployment process automatically.

### Option 2: Use the DNS Script Directly

```bash
# Set your API token
export CLOUDFLARE_DNS_API_TOKEN="your-cloudflare-api-token"

# Get CNAME target from Vercel
vercel domains add myapp.nazha.co
# Vercel will output: CNAME myapp.nazha.co [project-specific-target].vercel-dns-017.com

# Run the DNS setup with the project-specific CNAME target
node ~/.claude/skills/deploy-project/setup-cloudflare-dns.js \
  myapp \
  nazha.co \
  [project-specific-target].vercel-dns-017.com
```

### Option 3: Manual Step-by-Step

See `SKILL.md` for detailed step-by-step instructions.

## Complete Deployment Example

```bash
# 1. Initialize and commit
git init
git add .
git commit -m "Initial commit"

# 2. Create GitHub repo
gh repo create myapp --public --source=. --remote=origin
git push -u origin main

# 3. Deploy to Vercel
vercel --yes --prod

# 4. Add domain to Vercel and get CNAME target
CNAME_TARGET=$(vercel domains add myapp.nazha.co 2>&1 | grep -oE '[a-f0-9]+\.vercel-dns-[0-9]+\.com' | head -1)
# Or copy from Vercel dashboard if domain already exists

# 5. Configure DNS (automated)
export CLOUDFLARE_DNS_API_TOKEN="your-cloudflare-api-token"
node ~/.claude/skills/deploy-project/setup-cloudflare-dns.js \
  myapp nazha.co "$CNAME_TARGET"

# Done! Your app is live at:
# - https://myapp.vercel.app
# - https://myapp.nazha.co
```

## DNS Script Features

The `setup-cloudflare-dns.js` script:
- ✅ Validates all inputs
- ✅ Gets Zone ID automatically
- ✅ Checks for existing DNS records
- ✅ Prevents accidental overwrites (use `--force` to update)
- ✅ Supports Cloudflare proxy (`--proxied` flag)
- ✅ Shows clear error messages
- ✅ Zero dependencies (only Node.js built-ins)

## Usage Examples

### Basic CNAME for Vercel (Recommended)
```bash
# Get project-specific CNAME from Vercel dashboard or CLI output
node setup-cloudflare-dns.js myapp nazha.co 9931e99872af7dfe.vercel-dns-017.com
```

### With Cloudflare Proxy (DDoS protection, CDN)
```bash
node setup-cloudflare-dns.js api nazha.co backend.example.com --proxied
```

### Update Existing Record
```bash
node setup-cloudflare-dns.js myapp nazha.co new-target.com --force
```

### Other Platforms
```bash
# Netlify
node setup-cloudflare-dns.js site nazha.co mysite.netlify.app

# Heroku
node setup-cloudflare-dns.js app nazha.co myapp.herokuapp.com

# Custom server
node setup-cloudflare-dns.js api nazha.co server.example.com
```

## Credentials

All credentials are stored in `SKILL.md`:
- GitHub (gh CLI should already be authenticated)
- Vercel (authenticated via GitHub OAuth)
- Cloudflare API token (in environment variable)

## Requirements

### CLI Tools
- `gh` - GitHub CLI
- `vercel` - Vercel CLI
- `node` - Node.js runtime
- `git` - Version control

### Install Missing Tools
```bash
# GitHub CLI
brew install gh
gh auth login

# Vercel CLI
npm install -g vercel
vercel login

# Node.js (if not installed)
brew install node
```

## Verification

After deployment, verify everything works:

```bash
# Check GitHub repo
gh repo view

# Check Vercel deployment
vercel ls

# Check DNS
dig myapp.nazha.co CNAME +short

# Test HTTPS
curl -I https://myapp.nazha.co
```

Expected:
- GitHub repo is public and contains your code
- Vercel shows "Ready" status
- DNS returns project-specific CNAME target (e.g., `9931e99872af7dfe.vercel-dns-017.com`)
- HTTPS returns `HTTP/2 200` with `server: Vercel`

## Troubleshooting

### DNS Record Already Exists
```bash
# Check existing record
dig myapp.nazha.co CNAME +short

# Update with --force flag (use project-specific CNAME from Vercel)
node setup-cloudflare-dns.js myapp nazha.co 9931e99872af7dfe.vercel-dns-017.com --force
```

### Vercel Domain Not Verified
1. Wait 2-5 minutes for DNS propagation
2. Check Vercel project → Settings → Domains
3. Click "Refresh" if status shows pending

### API Token Invalid
1. Go to https://dash.cloudflare.com/profile/api-tokens
2. Verify token has "Edit zone DNS" permission for nazha.co
3. Create a new token if needed
4. Update environment variable

## Security Notes

- API token is stored in environment variable (not in files)
- Never commit tokens to git repositories
- Rotate tokens periodically for security
- Use project-specific tokens when possible

## Support

- Skill documentation: `~/.claude/skills/deploy-project/SKILL.md`
- Cloudflare API: https://developers.cloudflare.com/api/
- Vercel docs: https://vercel.com/docs
- GitHub CLI: https://cli.github.com/manual/

## Updates

To update this skill:
1. Edit `SKILL.md` for process changes
2. Edit `setup-cloudflare-dns.js` for script improvements
3. Update `README.md` for documentation changes

All changes take effect immediately in Claude Code.
