const fs = require('fs');

// ERROR 1: Prototype Pollution (Logic/Security)
// We are adding a method to ALL objects in the system. 
// If a hacker sends input like {"isAdmin": true}, checking if (user.isAdmin) might return true 
// because of how some libraries merge objects.
Object.prototype.log = function() {
    console.log(JSON.stringify(this));
}

var USERS_DB = [
    { id: 1, username: "admin", password: "supersecretpassword", role: "admin" },
    { id: 2, username: "guest", password: "guestpassword", role: "user" }
];

function AuthSystem() {
    // ERROR 2: Variable Hoisting / Scope
    // 'config' is defined inside the if block with 'var'. 
    // In JS, this hoists it to the top of the function but initialized as undefined.
    // If we try to access it before the assignment, it won't crash (like let/const), 
    // it will just be undefined, causing silent logic errors later.
    if (true) {
        var config = { sessionTimeout: 3000 };
    }
    this.config = config;
    this.sessions = {};
}

AuthSystem.prototype.login = function(username, password, callback) {
    // ERROR 3: Type Coercion Security Bypass
    // If the user sends a password as the boolean `true` (via JSON payload),
    // and the DB password is "guestpassword" (a non-empty string),
    // ("guestpassword" == true) evaluates to FALSE in JS.
    // However, if we had 1 == true, it is true.
    // BUT: If the hacker sends `0` and the password stored is `0`, `0 == 0` is true.
    // The real bug here is allowing the loop to continue even if no user is found.
    
    var foundUser = null;
    
    // ERROR 4: Blocking the Event Loop (Performance)
    // This 'while' loop runs synchronously. If USERS_DB has 1 million users,
    // the entire Node.js server freezes. No other requests can be handled.
    // It should be non-blocking or use async lookup.
    var start = Date.now();
    while (Date.now() - start < 100) { 
        // Simulating a "slow" DB hashing delay artificially
    }

    for (var i = 0; i < USERS_DB.length; i++) {
        var u = USERS_DB[i];
        if (u.username === username) {
            foundUser = u;
            break;
        }
    }

    if (!foundUser) {
        // ERROR 5: Improper Error Handling
        // calling callback("User not found") sets the error as a string.
        // Standard Node.js pattern is callback(Error, result).
        // Later code might try .message on the error and fail.
        return callback("User not found");
    }

    // ERROR 6: Coercion Bug
    // If the user sends the number 12345 and the stored password is string "12345", 
    // this returns true. This is weak security. Should use ===.
    if (password == foundUser.password) {
        // ERROR 7: "this" Context Loss
        // inside setTimeout, 'this' refers to the Timeout object (or global), 
        // not the AuthSystem instance. 'this.sessions' will be undefined.
        setTimeout(function() {
            var token = Math.random().toString(36);
            this.sessions[token] = foundUser.id;
            callback(null, token);
        }, 100);
    } else {
        callback(new Error("Invalid password"));
    }
}

// ERROR 8: Syntax / Reference Error
// We are trying to add a property to the function definition, not the prototype.
// 'AuthSystem.logout' does not exist on the instance 'auth'.
AuthSystem.logout = function(token) {
    console.log("Logging out " + token);
}

// MAIN EXECUTION
var auth = new AuthSystem();

// ERROR 9: Callback Hell / Logic
// The callback expects (err, token), but here we perform no error checking.
// If err is present, 'token' is undefined, and printing it prints "undefined".
auth.login("admin", "supersecretpassword", function(err, token) {
    if (err) console.log(err);
    
    console.log("Logged in with token: " + token);
    
    // ERROR 10: Calling the wrong method
    // 'auth' is an instance. 'logout' was defined as a static method on the class constructor.
    // auth.logout() is not a function.
    try {
        auth.logout(token);
    } catch(e) {
        console.log("Crash detected: " + e.message);
    }
});