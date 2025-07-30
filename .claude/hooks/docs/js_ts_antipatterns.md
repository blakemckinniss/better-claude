# JavaScript/TypeScript Anti-Pattern Detection

The PostToolUse hook now includes comprehensive anti-pattern detection for JavaScript and TypeScript files, automatically checking for security vulnerabilities, performance issues, and React-specific problems after modifications.

## Overview

When Claude modifies a JavaScript/TypeScript file (`.js`, `.jsx`, `.ts`, `.tsx`), the PostToolUse hook will:

1. **Format the code** using Prettier (if available)
2. **Scan for critical anti-patterns** including security vulnerabilities
3. **Report critical issues to Claude** via stderr with exit code 2, blocking the modification

## Anti-Patterns Detected

### 1. Security Vulnerabilities

#### Exposed Secrets
- **API Keys**: Detects hardcoded API keys in code
- **JWT Secrets**: Identifies hardcoded JWT signing secrets
- **Environment Fallbacks**: Warns about hardcoded fallbacks for environment variables

```javascript
// CRITICAL: These will be blocked
const API_KEY = "sk-proj-abcdef1234567890abcdef1234567890";
const token = jwt.sign(data, "hardcoded-secret");
```

#### Code Injection
- **eval() with user input**: Detects dangerous eval usage
- **new RegExp() with user input**: Identifies ReDoS vulnerabilities

```javascript
// CRITICAL: These will be blocked
eval(req.body.code);
new RegExp(req.params.pattern);
```

#### XSS Vulnerabilities
- **innerHTML with user input**: Detects DOM-based XSS
- **dangerouslySetInnerHTML with user input**: React-specific XSS

```javascript
// CRITICAL: These will be blocked
element.innerHTML = req.body.html;
<div dangerouslySetInnerHTML={{ __html: req.body.content }} />
```

#### SQL Injection
- **Template literals with user input**: Detects SQL injection in template strings

```javascript
// CRITICAL: This will be blocked
const query = `SELECT * FROM users WHERE id = ${req.params.id}`;
```

#### Command Injection
- **exec/spawn with user input**: Detects OS command injection

```javascript
// CRITICAL: These will be blocked
exec(`ls ${req.query.path}`);
spawn('echo', [req.body.input], { shell: true });
```

#### Configuration Issues
- **CORS wildcard**: Warns about overly permissive CORS
- **CSRF disabled**: Warns about disabled CSRF protection

```javascript
// WARNING: These will generate warnings
res.header('Access-Control-Allow-Origin', '*');
const config = { csrf: false };
```

### 2. Performance Anti-Patterns

#### Deprecated/Blocking Operations
- **document.write()**: Blocks HTML parsing
- **Synchronous XMLHttpRequest**: Deprecated and blocks the main thread

```javascript
// WARNING: These will generate warnings
document.write('<div>Content</div>');
xhr.open('GET', '/api', false); // sync request
```

#### Async Issues
- **Missing await**: Detects Promise-returning functions without await
- **Array operations in loops**: Suggests functional alternatives

```javascript
// WARNING: These will generate warnings
async function getData() {
    const data = fetch('/api'); // Missing await
}

for (let i = 0; i < items.length; i++) {
    results.push(items[i] * 2); // Use map() instead
}
```

### 3. React-Specific Anti-Patterns

#### State Management
- **Direct state mutation**: Both class and functional components

```javascript
// CRITICAL: These will be blocked
this.state.count = 5; // Class component
state.user = newUser; // Functional component
```

#### Performance Issues
- **Missing key prop**: In list rendering
- **Binding in render**: Creates new functions on every render
- **useEffect without dependencies**: Causes infinite re-renders

```javascript
// WARNING: These will generate warnings
items.map(item => <li>{item}</li>); // Missing key

<button onClick={this.handleClick.bind(this)}>Click</button>

useEffect(() => {
    // Runs on every render!
});
```

## Example Output

When critical anti-patterns are detected:

```
🔍 Checking for JavaScript/TypeScript anti-patterns...

🚨 CRITICAL JAVASCRIPT/TYPESCRIPT ANTI-PATTERNS DETECTED:
──────────────────────────────────────────────────

Security Issue at line 15:
  CRITICAL: SQL injection via template literal!
  Code: `SELECT * FROM users WHERE id = ${req.params.id}`

React Issue at line 42:
  CRITICAL: Direct state mutation in React! Use setState!
  Code: this.state.isOpen = true

──────────────────────────────────────────────────
🛑 BLOCKING: These critical JavaScript/TypeScript issues must be fixed!
   Claude will be notified immediately.
```

## Severity Levels

- **CRITICAL**: Blocks the file modification and notifies Claude
  - Security vulnerabilities (XSS, SQL injection, code injection)
  - React state mutations
  - Exposed secrets and API keys

- **WARNING**: Logged but doesn't block modification
  - Performance issues
  - Deprecated APIs
  - Best practice violations

## Best Practices to Avoid Anti-Patterns

### Security
1. Never hardcode secrets - use environment variables
2. Always sanitize user input before using in queries or DOM
3. Use parameterized queries or ORMs for database access
4. Avoid `eval()` and `new Function()` with user input
5. Configure CORS and CSRF properly

### Performance
1. Use `async/await` consistently
2. Prefer functional array methods over loops
3. Avoid synchronous operations in the browser
4. Use modern APIs instead of deprecated ones

### React
1. Always use `setState()` or state setters
2. Include `key` props in lists
3. Specify dependency arrays for hooks
4. Avoid creating functions in render

## Configuration

The anti-pattern detection runs automatically on all JavaScript and TypeScript files. No configuration is needed.

### Disabling Checks

If needed, you can temporarily disable checks by modifying the PostToolUse hook or removing it from your `.claude/settings.json`.

## Future Enhancements

- Vue.js specific patterns
- Angular specific patterns
- Node.js security patterns (file system, crypto)
- TypeScript-specific type safety issues
- Performance profiling patterns
- Accessibility anti-patterns