#!/bin/bash
# Run SessionStart .gitignore verification script.
#
# This script executes the comprehensive verification suite for the SessionStart hook's
# .gitignore handling capabilities.

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the absolute path to the project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Since we're in .claude/hooks/scripts, go up 3 levels to get to project root
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
VERIFICATION_SCRIPT="$PROJECT_ROOT/.claude/hooks/tests/sessionstart_gitignore_verification.py"

echo -e "${YELLOW}SessionStart .gitignore Verification Runner${NC}"
echo "=================================================="
echo "Project root: $PROJECT_ROOT"
echo "Verification script: $VERIFICATION_SCRIPT"
echo ""

# Check if verification script exists
if [[ ! -f "$VERIFICATION_SCRIPT" ]]; then
    echo -e "${RED}Error: Verification script not found at $VERIFICATION_SCRIPT${NC}"
    exit 1
fi

# Check if script is executable
if [[ ! -x "$VERIFICATION_SCRIPT" ]]; then
    echo "Making verification script executable..."
    chmod +x "$VERIFICATION_SCRIPT"
fi

# Parse arguments
VERBOSE=""
if [[ "$1" == "--verbose" || "$1" == "-v" ]]; then
    VERBOSE="--verbose"
    echo -e "${YELLOW}Running in verbose mode${NC}"
fi

if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    python3 "$VERIFICATION_SCRIPT" --help
    exit 0
fi

# Run the verification
echo -e "${YELLOW}Starting verification...${NC}"
echo ""

if python3 "$VERIFICATION_SCRIPT" $VERBOSE; then
    echo ""
    echo -e "${GREEN}✅ SessionStart .gitignore verification PASSED${NC}"
    echo -e "${GREEN}The SessionStart hook properly respects .gitignore rules${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}❌ SessionStart .gitignore verification FAILED${NC}"
    echo -e "${RED}The SessionStart hook has issues with .gitignore handling${NC}"
    echo ""
    echo -e "${YELLOW}Troubleshooting tips:${NC}"
    echo "• Check that git is properly installed and configured"
    echo "• Verify the SessionStart.py module can be imported"
    echo "• Run with --verbose flag for detailed output"
    echo "• Check the SessionStart hook implementation for bugs"
    exit 1
fi