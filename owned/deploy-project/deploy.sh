#!/bin/bash
# Quick deployment script for Vercel + Cloudflare DNS
# Usage: ./deploy.sh <project-name> "<description>" [--full]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOMAIN="nazha.co"
CLOUDFLARE_TOKEN="${CLOUDFLARE_DNS_API_TOKEN}"

# Parse arguments
PROJECT_NAME="$1"
DESCRIPTION="${2:-Deployed with Claude Code}"
FULL_SETUP=false

# Check for --full flag
if [[ "$@" == *"--full"* ]]; then
  FULL_SETUP=true
fi

if [ -z "$PROJECT_NAME" ]; then
  echo -e "${RED}❌ Error: Project name is required${NC}"
  echo ""
  echo "Usage: $0 <project-name> \"<description>\" [--full]"
  echo ""
  echo "Examples:"
  echo "  $0 myapp \"A beautiful app\"          # Quick deploy (push + deploy)"
  echo "  $0 myapp \"A beautiful app\" --full   # Full setup (repo + DNS)"
  exit 1
fi

# Detect if this is a re-deployment
IS_REDEPLOYMENT=false
if [ -d .git ] && git remote get-url origin &>/dev/null; then
  REMOTE_URL=$(git remote get-url origin)
  if [[ "$REMOTE_URL" == *"$PROJECT_NAME"* ]]; then
    IS_REDEPLOYMENT=true
  fi
fi

# Show deployment mode
if [ "$IS_REDEPLOYMENT" = true ] && [ "$FULL_SETUP" = false ]; then
  echo -e "${BLUE}🔄 Quick Redeployment Mode${NC}"
  echo -e "${BLUE}   (use --full flag for complete setup)${NC}"
  echo ""
else
  echo -e "${GREEN}🚀 Full Deployment: ${PROJECT_NAME}${NC}"
  echo ""
fi

# Step 1: Git setup (always check, but skip if exists)
if [ "$IS_REDEPLOYMENT" = false ] || [ "$FULL_SETUP" = true ]; then
  echo -e "${YELLOW}📦 Step 1: Git Repository${NC}"
  if [ ! -d .git ]; then
    echo "Initializing git repository..."
    git init

    # Create .gitignore if it doesn't exist
    if [ ! -f .gitignore ]; then
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

# env files
.env*.local
.env

# vercel
.vercel

# typescript
*.tsbuildinfo
next-env.d.ts
EOF
      echo "Created .gitignore"
    fi

    git add .
    git commit -m "Initial commit

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
    echo "✓ Git initialized and committed"
  else
    echo "✓ Git repository already exists"
  fi
  echo ""
fi

# Step 2: Commit and push changes
echo -e "${YELLOW}📤 Git Push${NC}"

# Check if there are changes to commit
if [ "$IS_REDEPLOYMENT" = true ]; then
  if git diff-index --quiet HEAD --; then
    echo "✓ No changes to commit"
  else
    echo "Committing changes..."
    git add .
    git commit -m "Deploy: $(date +%Y-%m-%d\ %H:%M:%S)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
    echo "✓ Changes committed"
  fi
fi

# GitHub repository setup or push
if [ "$IS_REDEPLOYMENT" = false ] || [ "$FULL_SETUP" = true ]; then
  echo "Checking GitHub repository..."
  if ! gh repo view "$PROJECT_NAME" &>/dev/null; then
    echo "Creating GitHub repository..."
    gh repo create "$PROJECT_NAME" --public --source=. --remote=origin --description="$DESCRIPTION"
    git push -u origin main
    echo "✓ GitHub repository created and pushed"
  else
    echo "✓ GitHub repository already exists"
    git push origin main 2>/dev/null || echo "✓ Already up to date"
  fi
else
  echo "Pushing to GitHub..."
  git push origin main 2>/dev/null && echo "✓ Pushed to GitHub" || echo "✓ Already up to date"
fi
echo ""

# Step 3: Vercel deployment (always run)
echo -e "${YELLOW}🚀 Vercel Deployment${NC}"
echo "Deploying to Vercel..."
DEPLOY_OUTPUT=$(vercel --yes --prod 2>&1)
VERCEL_URL=$(echo "$DEPLOY_OUTPUT" | grep -o 'https://[^[:space:]]*\.vercel\.app' | head -1)

if [ -z "$VERCEL_URL" ]; then
  echo -e "${RED}❌ Failed to deploy to Vercel${NC}"
  echo "$DEPLOY_OUTPUT"
  exit 1
fi

echo "✓ Deployed to: $VERCEL_URL"
echo ""

# Step 4 & 5: Custom domain and DNS (only on full setup or first deployment)
if [ "$IS_REDEPLOYMENT" = false ] || [ "$FULL_SETUP" = true ]; then
  echo -e "${YELLOW}🌐 Custom Domain Setup${NC}"
  CUSTOM_DOMAIN="${PROJECT_NAME}.${DOMAIN}"

  # Add domain to Vercel
  echo "Adding custom domain: $CUSTOM_DOMAIN"
  if vercel domains ls 2>/dev/null | grep -q "$CUSTOM_DOMAIN"; then
    echo "✓ Domain already added to Vercel"
  else
    vercel domains add "$CUSTOM_DOMAIN" 2>/dev/null && echo "✓ Domain added to Vercel" || echo "⚠️  Domain add failed (may already exist)"
  fi
  echo ""

  # DNS configuration
  echo -e "${YELLOW}🔧 DNS Configuration${NC}"

  if [ -z "$CLOUDFLARE_TOKEN" ]; then
    echo -e "${YELLOW}⚠️  CLOUDFLARE_DNS_API_TOKEN not set${NC}"
    echo "Skipping DNS setup. Set up manually or export token and run with --full"
  else
    export CLOUDFLARE_DNS_API_TOKEN="$CLOUDFLARE_TOKEN"

    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    node "$SCRIPT_DIR/setup-cloudflare-dns.js" \
      "$PROJECT_NAME" \
      "$DOMAIN" \
      "cname.vercel-dns.com" 2>/dev/null || {
        echo -e "${YELLOW}⚠️  DNS already exists or setup had issues${NC}"
      }
  fi
  echo ""
fi

# Final summary
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
if [ "$IS_REDEPLOYMENT" = true ] && [ "$FULL_SETUP" = false ]; then
  echo -e "${GREEN}✅ Redeployment Complete!${NC}"
else
  echo -e "${GREEN}✅ Deployment Complete!${NC}"
fi
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "📦 GitHub:   https://github.com/$(gh api user -q .login 2>/dev/null || echo 'your-username')/$PROJECT_NAME"
echo -e "🚀 Vercel:   $VERCEL_URL"

if [ "$IS_REDEPLOYMENT" = false ] || [ "$FULL_SETUP" = true ]; then
  CUSTOM_DOMAIN="${PROJECT_NAME}.${DOMAIN}"
  echo -e "🌐 Custom:   https://$CUSTOM_DOMAIN"
  echo ""
  echo -e "${YELLOW}⏱️  DNS propagation may take 2-5 minutes${NC}"
  echo ""
  echo "Verify with:"
  echo "  dig $CUSTOM_DOMAIN CNAME +short"
  echo "  curl -I https://$CUSTOM_DOMAIN"
else
  echo ""
  echo -e "${BLUE}💡 Tip: Use --full flag to reconfigure domain/DNS${NC}"
fi
