# Backend Redeployment Guide

## 🚀 **Quick Fix for Network Error**

### **Step 1: Check Render Dashboard**
1. Go to [render.com](https://render.com)
2. Find your backend service: `babcock-smart-campus-backend`
3. Check the service status

### **Step 2: Verify Environment Variables**
Make sure these are set in your Render backend service:

```
MONGODB_URL=mongodb+srv://bu22-2130:bu22-2130@cluster0.4nsgp2g.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0
MONGODB_DATABASE=smart_campus_db
SECRET_KEY=smart-campus-app-secret-key-2024-babcock-university
GOOGLE_MAPS_API_KEY=AIzaSyAa-XKO4DH_CLf647SMZYypDOfk0d1SBUE
```

### **Step 3: Verify Build Settings**
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### **Step 4: Manual Redeploy**
1. In Render dashboard, click "Manual Deploy"
2. Select "Clear build cache & deploy"
3. Wait for deployment to complete

### **Step 5: Test the Backend**
Once deployed, test these endpoints:
- Health Check: `https://babcock-smart-campus-backend.onrender.com/health`
- Root: `https://babcock-smart-campus-backend.onrender.com/`

### **Step 6: Test Login API**
```bash
curl -X POST https://babcock-smart-campus-backend.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@babcock.edu",
    "password": "test123"
  }'
```

## 🔧 **If Still Not Working**

### **Alternative: Deploy to Railway**
1. Go to [railway.app](https://railway.app)
2. Create new project
3. Connect your GitHub repository
4. Set environment variables
5. Deploy

### **Alternative: Deploy to Heroku**
1. Go to [heroku.com](https://heroku.com)
2. Create new app
3. Connect GitHub repository
4. Set environment variables
5. Deploy

## 📞 **Support**
If you continue having issues, check:
1. Render service logs for specific errors
2. MongoDB Atlas connection
3. Network connectivity
4. CORS settings 