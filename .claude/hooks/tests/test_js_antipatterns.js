#!/usr/bin/env node
/**
 * Test file with JavaScript anti-patterns to verify detection.
 */

// Test 1: Exposed API Key
const API_KEY = "sk-proj-abcdef1234567890abcdef1234567890";
const githubToken = "ghp_1234567890abcdef1234567890abcdef12";

// Test 2: Hardcoded environment fallback
const dbUrl = process.env.DATABASE_URL || "mongodb://admin:password@localhost";

// Test 3: eval() with user input
function dangerousEval(req) {
    const userCode = req.body.code;
    eval(userCode); // CRITICAL: Code injection!
}

// Test 4: innerHTML with user input
function createContent(req) {
    const element = document.getElementById('content');
    element.innerHTML = req.params.html; // CRITICAL: XSS vulnerability!
}

// Test 5: SQL injection in template literal
function getUser(req) {
    const userId = req.params.id;
    const query = `SELECT * FROM users WHERE id = ${userId}`; // CRITICAL: SQL injection!
    return query;
}

// Test 6: Command injection
const { exec } = require('child_process');
function runCommand(req) {
    const cmd = req.query.command;
    exec(`ls ${cmd}`, (err, stdout) => { // CRITICAL: Command injection!
        console.log(stdout);
    });
}

// Test 7: Unsafe regex with user input
function validateInput(req) {
    const pattern = req.body.pattern;
    const regex = new RegExp(pattern); // CRITICAL: ReDoS vulnerability!
    return regex.test("some text");
}

// Test 8: CORS wildcard
app.use((req, res, next) => {
    res.header('Access-Control-Allow-Origin', '*'); // WARNING: Allows any origin!
    next();
});

// Test 9: CSRF disabled
const sessionConfig = {
    secret: 'keyboard cat',
    csrf: false // WARNING: CSRF protection disabled!
};

// Test 10: Hardcoded JWT secret
const jwt = require('jsonwebtoken');
function createToken(user) {
    return jwt.sign(user, 'super-secret-key'); // CRITICAL: Hardcoded secret!
}

// Test 11: document.write
function oldSchoolWrite() {
    document.write('<h1>Hello World</h1>'); // WARNING: Blocks parsing!
}

// Test 12: Synchronous XHR
function syncRequest() {
    const xhr = new XMLHttpRequest();
    xhr.open('GET', '/api/data', false); // WARNING: Synchronous request!
    xhr.send();
}

// Test 13: Missing await
async function fetchData() {
    const data = fetch('/api/users'); // WARNING: Missing await!
    console.log(data); // This logs a Promise, not the data
}

// Test 14: Array push in loop
function inefficientArray(items) {
    const results = [];
    for (let i = 0; i < items.length; i++) {
        results.push(items[i] * 2); // WARNING: Use map instead!
    }
    return results;
}

// Test 15: React - Direct state mutation
class BadComponent extends React.Component {
    handleClick() {
        this.state.count = this.state.count + 1; // CRITICAL: Direct mutation!
    }
}

// Test 16: React - Missing key in list
function ListComponent({ items }) {
    return (
        <ul>
            {items.map(item => <li>{item.name}</li>)} {/* WARNING: Missing key! */}
        </ul>
    );
}

// Test 17: React - Unsafe dangerouslySetInnerHTML
function UnsafeComponent({ req }) {
    return (
        <div 
            dangerouslySetInnerHTML={{ __html: req.body.content }} // CRITICAL: XSS!
        />
    );
}

// Test 18: React - useEffect without dependencies
function InfiniteRenderComponent() {
    React.useEffect(() => {
        console.log('This runs on every render!');
    }); // WARNING: Missing dependency array!
}

// Test 19: React - Binding in render
function BindingComponent() {
    return (
        <button onClick={this.handleClick.bind(this)}> {/* WARNING: New function every render! */}
            Click me
        </button>
    );
}

console.log("This test file contains intentional anti-patterns for testing.");