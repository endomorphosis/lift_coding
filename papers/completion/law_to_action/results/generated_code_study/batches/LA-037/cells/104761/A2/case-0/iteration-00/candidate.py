# JWT auth, verification, binding, password hashing, and expiry in Go with supanadit/jwt-go
## Background
This skill shows how to use the Go library `github.com/supanadit/jwt-go` to:
- Set a JWT secret
- Generate and verify JWTs from either the library's default `Authorization` model or your own struct
- Verify and bind (decode) a JWT back into a struct
- Hash and verify passwords using bcrypt (on
## Key Features
- Supports both symmetric (HS256) and asymmetric (RS256) algorithms
- Provides helper functions for common operations
- Includes detailed error handling
- Supports custom claims
- Provides methods for token expiration handling

## Installation
To install this skill, run:
```bash
skill install github.com/supanadit/jwt-go
```

## Usage
### Generating a Token
```go
func generateToken(userID string) (string, error) {
	token := jwt.NewToken(userID)
	tokenString, err := token.GenerateToken()
	if err != nil {
		return "", err
	}

	return tokenString, nil
}

### Verifying a Token
```go
func verifyToken(tokenString string) (bool, error) {
	token, err := jwt.ParseToken(tokenString)
	if err != nil {
		return false, err
	}

	return token.Verify()
}

### Binding a Token
```go
func bindToken(tokenString string) (string, error) {