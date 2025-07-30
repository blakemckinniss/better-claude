#!/usr/bin/env node
/**
 * Test specific pattern matching for JavaScript anti-patterns
 */

// These SHOULD be detected based on our patterns:

// Pattern: \beval\s*\([^)]*(?:request|req|params|body|query)
const userInput = req.body.code;
eval(userInput); // Should match

// Pattern: `[^`]*(?:SELECT|INSERT|UPDATE|DELETE)[^`]*\$\{[^}]*(?:request|req|params|body|query)
const query1 = `SELECT * FROM users WHERE id = ${req.params.id}`; // Should match
const query2 = `DELETE FROM posts WHERE user = ${req.body.userId}`; // Should match

// Let's also test the exact patterns from test_js_antipatterns2.js that weren't caught:

// This exact line from test_js_antipatterns2.js - eval
const result = eval(req.body.code); // Should match

// This exact line from test_js_antipatterns2.js - SQL  
return db.query(`DELETE FROM users WHERE id = ${req.query.id}`); // Should match