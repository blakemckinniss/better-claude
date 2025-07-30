#!/usr/bin/env node
/**
 * Additional JavaScript anti-pattern tests focusing on patterns that weren't detected yet.
 */

// Test eval() with user input - should be detected
app.post('/eval', (req, res) => {
    const code = req.body.code;
    const result = eval(code); // CRITICAL: Code injection
    res.json({ result });
});

// Test SQL injection - should be detected
function deleteUser(req) {
    const id = req.query.id;
    return db.query(`DELETE FROM users WHERE id = ${id}`); // CRITICAL
}

// Test command injection - should be detected
const { spawn } = require('child_process');
app.get('/run', (req, res) => {
    spawn('echo', [req.query.input], { shell: true }); // CRITICAL
});

// Test ReDoS - should be detected
function validateEmail(req) {
    const emailPattern = req.body.emailRegex;
    const emailRegex = new RegExp(emailPattern); // CRITICAL: ReDoS
    return emailRegex.test("user@example.com");
}

// Test exposed API key - should be detected
const config = {
    apiKey: "AKIAIOSFODNN7EXAMPLE123456789012", // CRITICAL
    secret: "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
};

// Test hardcoded JWT secret - should be detected
const jsonwebtoken = require('jsonwebtoken');
const token = jsonwebtoken.sign({ id: 1 }, "my-secret-key-123"); // CRITICAL