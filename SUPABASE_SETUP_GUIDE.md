# Supabase Database Setup Guide

## 🎯 Overview
The Video Merger API has full Supabase support with pre-built schema and integration.

## 📋 Step 1: Create Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Click "Start your project" 
3. Create new organization (if needed)
4. Click "New Project"
5. Fill in:
   - **Name**: `video-merger-api`
   - **Database Password**: Generate strong password
   - **Region**: Choose closest to your users
6. Click "Create new project"

## 🔧 Step 2: Run Database Schema

1. Go to your Supabase project dashboard
2. Click "SQL Editor" in the left sidebar
3. Click "New Query"
4. Copy and paste the entire contents of `database/schema.sql`
5. Click "Run" to execute the schema

**The schema creates:**
- ✅ Users table with subscription tiers
- ✅ API keys table with rate limiting
- ✅ User credits table with automatic calculations
- ✅ Credit transactions table for audit trail
- ✅ Processing jobs table for job management
- ✅ Indexes for performance
- ✅ Row Level Security (RLS) policies

## 🔑 Step 3: Get Supabase Credentials

1. In your Supabase project dashboard
2. Go to "Settings" → "API"
3. Copy these values:

```bash
# Project URL
SUPABASE_URL=https://your-project-id.supabase.co

# Anon/Public Key (for client-side)
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Service Role Key (for server-side - KEEP SECRET!)
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## ⚙️ Step 4: Update Environment Configuration

Update your `.env` file:

```bash
# Database Configuration - CHANGE THESE
USE_SQLITE=false
DATABASE_URL=postgresql://postgres:your-db-password@db.your-project-id.supabase.co:5432/postgres

# Supabase Configuration - ADD THESE
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_KEY=your-service-key-here

# Keep other settings as they are
USE_LOCAL_STORAGE=false  # Will use Supabase Storage
```

## 🗂️ Step 5: Setup Supabase Storage

1. In Supabase dashboard, go to "Storage"
2. Click "Create bucket"
3. Create bucket named: `video-processing`
4. Set it as **Public** bucket
5. Go to "Policies" tab
6. Add policy for uploads:

```sql
-- Allow authenticated uploads
CREATE POLICY "Allow authenticated uploads" ON storage.objects
FOR INSERT WITH CHECK (auth.role() = 'authenticated');

-- Allow public downloads
CREATE POLICY "Allow public downloads" ON storage.objects
FOR SELECT USING (bucket_id = 'video-processing');
```

## 🧪 Step 6: Test Connection

Run this test to verify connection:

```bash
# Test database connection
curl -X GET "http://localhost:8001/health" \
  -H "Content-Type: application/json"

# Should return:
{
  "status": "healthy",
  "services": {
    "database": true,
    "storage": true,
    "ffmpeg": true
  }
}
```

## 🔄 Step 7: Data Migration (if needed)

If you have existing SQLite data to migrate:

```python
# Run this script to migrate data
python scripts/migrate_to_supabase.py
```

## 📊 Step 8: Verify Tables

In Supabase SQL Editor, run:

```sql
-- Check all tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- Should show:
-- api_keys
-- credit_transactions  
-- processing_jobs
-- user_credits
-- users
```

## 🎯 Benefits of Supabase Integration

✅ **Scalable PostgreSQL** - Production-ready database
✅ **Real-time subscriptions** - Live updates for job status
✅ **Built-in authentication** - User management system
✅ **File storage** - Integrated storage for video files
✅ **Dashboard** - Visual database management
✅ **Automatic backups** - Point-in-time recovery
✅ **Global CDN** - Fast file delivery worldwide

## 🔒 Security Features

✅ **Row Level Security** - Users can only access their data
✅ **API key validation** - Secure authentication
✅ **Rate limiting** - Built into database schema
✅ **Audit trails** - All transactions logged

## 📈 Monitoring

Monitor your database in Supabase dashboard:
- **Database** → View tables and data
- **API** → Monitor API usage
- **Storage** → Track file uploads/downloads
- **Logs** → Debug issues

Your app will automatically switch to Supabase when you update the environment variables!
