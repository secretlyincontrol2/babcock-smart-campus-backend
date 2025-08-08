# Smart Campus App Backend

A FastAPI backend for the Babcock University Smart Campus App using MongoDB.

## Features

- User authentication and authorization
- QR code-based attendance system
- Cafeteria menu management
- Campus map integration with Google Maps
- Class schedule management
- Chat system for classmates
- User profile management

## Railway Deployment with MongoDB

### Prerequisites

1. Railway account
2. GitHub repository with this code
3. MongoDB Atlas account (free tier available)

### Deployment Steps

1. **Connect to Railway:**
   - Go to [Railway.app](https://railway.app)
   - Sign in with GitHub
   - Click "New Project"
   - Select "Deploy from GitHub repo"

2. **Configure Environment Variables:**
   - Go to your project settings
   - Add these environment variables:
     ```
     SECRET_KEY=your-secret-key-here
     GOOGLE_MAPS_API_KEY=AIzaSyAa-XKO4DH_CLf647SMZYypDOfk0d1SBUE
     MONGODB_URL=your-mongodb-atlas-connection-string
     MONGODB_DATABASE=smart_campus_db
     ```

3. **Set up MongoDB Atlas:**
   - Go to [MongoDB Atlas](https://www.mongodb.com/atlas)
   - Create a free cluster
   - Get your connection string
   - Add it to Railway environment variables

4. **Deploy:**
   - Railway will automatically deploy when you push to your GitHub repository
   - The app will be available at your Railway URL

### Local Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up environment variables in `.env` file:
   ```
   MONGODB_URL=mongodb://localhost:27017
   MONGODB_DATABASE=smart_campus_db
   SECRET_KEY=your-secret-key-here
   GOOGLE_MAPS_API_KEY=AIzaSyAa-XKO4DH_CLf647SMZYypDOfk0d1SBUE
   ```

3. Run the server:
   ```bash
   uvicorn app.main:app --reload
   ```

## API Documentation

Once deployed, visit `https://your-railway-url.railway.app/docs` for interactive API documentation.

## Test User

After deployment, you can create a test user using the API:

```bash
curl -X POST "https://your-railway-url.railway.app/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "BU2024001",
    "email": "test@babcock.edu",
    "full_name": "Test Student",
    "password": "test123",
    "department": "Computer Science",
    "level": "300"
  }'
```

## MongoDB Setup

### MongoDB Atlas (Recommended)

1. **Create Account:**
   - Go to [MongoDB Atlas](https://www.mongodb.com/atlas)
   - Sign up for a free account

2. **Create Cluster:**
   - Click "Build a Database"
   - Choose "FREE" tier
   - Select your preferred cloud provider and region
   - Click "Create"

3. **Set Up Database Access:**
   - Go to "Database Access"
   - Click "Add New Database User"
   - Create a username and password
   - Select "Read and write to any database"
   - Click "Add User"

4. **Set Up Network Access:**
   - Go to "Network Access"
   - Click "Add IP Address"
   - Click "Allow Access from Anywhere" (for Railway)
   - Click "Confirm"

5. **Get Connection String:**
   - Go to "Database"
   - Click "Connect"
   - Choose "Connect your application"
   - Copy the connection string
   - Replace `<password>` with your database user password
   - Add to Railway environment variables

### Local MongoDB (Development)

1. Install MongoDB locally
2. Start MongoDB service
3. Use connection string: `mongodb://localhost:27017` 