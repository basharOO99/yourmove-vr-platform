# Database Migration Guide - v1.x to v2.0

## 🗄️ Database Compatibility

Your uploaded `yourmove.db` from v1.x should be mostly compatible with v2.0, but may need schema updates.

## Schema Comparison

### v1.x Schema (Your Upload)
```sql
doctors:
  - id (INTEGER, PRIMARY KEY)
  - username (VARCHAR(50), UNIQUE)
  - hashed_password (VARCHAR(255))
  - full_name (VARCHAR(100))
  - email (VARCHAR(100), UNIQUE)
  - created_at (DATETIME)

patients:
  - id (INTEGER, PRIMARY KEY)
  - name (VARCHAR(100))
  - age (INTEGER)
  - gender (VARCHAR(20))  -- Added in recent update
  - diagnosis_level (VARCHAR(50))
  - notes (TEXT)
  - created_at (DATETIME)
```

### v2.0 Schema (Optimized Version)
**Identical structure** - fully compatible! ✅

## Migration Options

### Option 1: Use Existing Database (If You Have Important Data)

```bash
# 1. Backup your existing database
cp /path/to/old/yourmove.db yourmove.db.backup

# 2. Copy to v2.0 folder
cp /path/to/old/yourmove.db /path/to/yourmove_optimized/

# 3. Verify schema compatibility
sqlite3 yourmove.db
.schema doctors
.schema patients
.quit

# 4. Start v2.0 (it will use your existing database)
python main.py
```

### Option 2: Fresh Database (Recommended for Testing)

```bash
# 1. Start v2.0 without old database
cd yourmove_optimized
rm yourmove.db  # Remove if exists
python main.py  # Creates fresh database

# Default credentials: admin / admin123
```

### Option 3: Merge Data Manually

If you want to keep specific patients but start fresh:

```bash
# 1. Export data from old database
sqlite3 /path/to/old/yourmove.db
.mode csv
.output patients_export.csv
SELECT * FROM patients;
.quit

# 2. Start v2.0 with fresh database
cd yourmove_optimized
python main.py

# 3. Use dashboard to manually re-add important patients
# Or write a script to import from CSV
```

## Verification Steps

After migration, verify:

1. **Login Works**
   ```bash
   # Test at http://localhost:8000/login
   # Username: admin
   # Password: admin123
   ```

2. **Patients Display Correctly**
   ```bash
   # Go to Dashboard → Patient Management
   # Check all fields display properly
   ```

3. **Gender Field Exists**
   ```bash
   sqlite3 yourmove.db
   SELECT name, age, gender FROM patients;
   .quit
   ```

## Troubleshooting

### Error: "no such column: patients.gender"

Your old database doesn't have the gender column. Add it:

```bash
sqlite3 yourmove.db
ALTER TABLE patients ADD COLUMN gender VARCHAR(20) DEFAULT 'Other';
.quit
```

### Error: "database is locked"

```bash
# Close all connections
pkill -f "python main.py"
# Wait 5 seconds
python main.py
```

### Want to Reset Everything

```bash
rm yourmove.db
python main.py
# Fresh database with default admin account
```

## Data Preservation Tips

1. **Always backup before migrating**
   ```bash
   cp yourmove.db yourmove.db.backup_$(date +%Y%m%d)
   ```

2. **Test on a copy first**
   ```bash
   cp yourmove.db yourmove_test.db
   # Test with yourmove_test.db
   ```

3. **Export critical data**
   ```bash
   sqlite3 yourmove.db ".dump" > backup.sql
   ```

## Recommended Approach

For most users:

1. ✅ **Use v2.0 with fresh database** (easiest, safest)
2. ⚠️ **Manually re-add important patients** (5-10 minutes work)
3. 🎯 **Benefit from clean, optimized schema**

This ensures you get all v2.0 improvements without any legacy data issues.

---

**Need help?** The v2.0 version will automatically create a working database on first run!
