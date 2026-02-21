# Cartographer Auth Service

User authentication and authorization microservice for the Cartographer network mapping application.

## Features

- **First-run Setup**: Owner account creation on initial startup
- **JWT Authentication**: Secure token-based authentication
- **Role-based Access Control**:
  - `owner`: Full access - can manage users and modify network map
  - `readwrite`: Can view and modify the network map
  - `readonly`: Can only view the network map
- **User Management**: Create, update, and delete users (owner only)
- **Email Invitations**: Invite users via email using [Resend](https://resend.com)
- **Password Management**: Secure password hashing with bcrypt

## API Endpoints

### Setup
- `GET /api/auth/setup/status` - Check if initial setup is complete
- `POST /api/auth/setup/owner` - Create the initial owner account

### Authentication
- `POST /api/auth/login` - Authenticate and get access token
- `POST /api/auth/logout` - Logout (client-side token discard)
- `GET /api/auth/session` - Get current session info
- `POST /api/auth/verify` - Verify token validity
- `POST /api/auth/password-reset/request` - Request password reset email (public)
- `POST /api/auth/password-reset/confirm` - Reset password with token (public)

### User Management (Owner only)
- `GET /api/auth/users` - List all users
- `POST /api/auth/users` - Create a new user
- `GET /api/auth/users/{id}` - Get user by ID
- `PATCH /api/auth/users/{id}` - Update user
- `DELETE /api/auth/users/{id}` - Delete user

### Invitations (Owner only)
- `GET /api/auth/invites` - List all invitations
- `POST /api/auth/invites` - Create and send an invitation
- `GET /api/auth/invites/{id}` - Get invitation by ID
- `DELETE /api/auth/invites/{id}` - Revoke a pending invitation
- `POST /api/auth/invites/{id}/resend` - Resend invitation email

### Public Invitation Endpoints
- `GET /api/auth/invite/verify/{token}` - Verify invitation token
- `POST /api/auth/invite/accept` - Accept invitation and create account

### Profile
- `GET /api/auth/me` - Get current user profile
- `PATCH /api/auth/me` - Update current user profile
- `POST /api/auth/me/change-password` - Change password

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET` | `cartographer-dev-secret...` | Secret key for JWT signing (change in production!) |
| `JWT_EXPIRATION_HOURS` | `24` | Token expiration time in hours |
| `AUTH_DATA_DIR` | `/app/data` | Directory for persistent user data |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |
| `RESEND_API_KEY` | *(empty)* | Resend API key for sending invitation emails |
| `EMAIL_FROM` | `Cartographer <noreply@cartographer.app>` | Sender email address |
| `APPLICATION_URL` | `http://localhost:5173` | Public URL for invitation links |
| `INVITE_EXPIRATION_HOURS` | `72` | Invitation expiration time in hours |
| `PASSWORD_RESET_EXPIRATION_MINUTES` | `60` | Password reset token expiration in minutes |

### Email Configuration

Email invitations are **optional**. If `RESEND_API_KEY` is not set:
- Invitations are still created and stored
- The invite link is generated but no email is sent
- You can manually share the invite URL with users

To enable email invitations:
1. Sign up at [Resend](https://resend.com)
2. Create an API key
3. Verify your sending domain (or use Resend's test domain for development)
4. Set the environment variables:
   ```bash
   RESEND_API_KEY=re_your_api_key
   EMAIL_FROM=Cartographer <noreply@your-domain.com>
   APPLICATION_URL=https://your-app-url.com
   ```

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

## Docker

```bash
# Build
docker build -t cartographer-auth .

# Run
docker run -p 8002:8002 -v auth-data:/app/data cartographer-auth
```

## Security Notes

1. **Change `JWT_SECRET` in production** - The default is for development only
2. **Use HTTPS in production** - JWT tokens should only be transmitted over secure connections
3. **Password Requirements**: Minimum 8 characters
4. **Token Expiration**: Tokens expire after 24 hours by default

## Data Persistence

Data is stored in JSON format in `$AUTH_DATA_DIR`:
- `users.json` - User accounts
- `invites.json` - Pending and historical invitations

Mount a volume to persist data across container restarts.
