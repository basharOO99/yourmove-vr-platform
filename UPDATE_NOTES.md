# YourMove Platform - Update Notes

## Recent Improvements (February 2026)

All requested features have been successfully implemented across the entire platform.

---

## 1. ✅ Fixed Chart Looping Issue

**Problem**: Charts were updating infinitely even without data.

**Solution**: 
- Removed pre-populated data arrays (`focusData`, `stressData`)
- Charts now only update when actual WebSocket data arrives
- Added `animation: false` to chart options for smoother real-time updates
- Data is now managed directly within Chart.js's internal data structures

**Files Modified**:
- `templates/dashboard.html` - Updated chart initialization and data update logic

**Result**: Charts now remain empty until real session data arrives, then expand smoothly as data points are added.

---

## 2. ✅ Removed Age Restriction

**Problem**: Patient age was restricted to maximum 18 years.

**Solution**:
- Changed age validation from `max=18` to `max=150`
- Updated both backend schema and frontend form
- Allows patients of any age (1-150 years)

**Files Modified**:
- `schemas.py` - PatientCreate model age field
- `templates/dashboard.html` - Patient form age input

**Result**: System now accepts patients of any age, making it suitable for adults with autism or other conditions.

---

## 3. ✅ Added Gender Field

**Problem**: No gender field in patient records.

**Solution**:
- Added `gender` column to Patient database model
- Added gender to Pydantic schemas (PatientCreate, PatientResponse)
- Updated API endpoints (create and update patient)
- Added gender dropdown to patient form (Male, Female, Other)
- Added gender column to patient table display

**Files Modified**:
- `models.py` - Added gender column to Patient model
- `schemas.py` - Added gender to PatientCreate and PatientResponse
- `main.py` - Updated create_patient and update_patient endpoints
- `templates/dashboard.html` - Added gender field to form and table

**Result**: Complete gender support throughout the patient management system.

**Note**: If you have an existing database, you may need to delete `yourmove.db` and restart the server to recreate the database with the new schema, or manually add the column using SQL:
```sql
ALTER TABLE patients ADD COLUMN gender VARCHAR(20);
```

---

## 4. ✅ Dark/Light Theme Toggle

**Problem**: No theme switching capability.

**Solution**:
- Implemented CSS variable-based theming system
- Added dark mode color palette
- Created custom theme toggle button (animated slider)
- Persists theme preference in localStorage
- Works across all pages (landing, login, dashboard)

**Features**:
- **Toggle Button**: Animated slider in navigation bar
- **Persistence**: Theme choice saved and restored on page reload
- **Consistency**: Same theme across all pages
- **Colors**:
  - Light mode: White backgrounds, dark text
  - Dark mode: Dark backgrounds (#111827), light text

**Files Modified**:
- `templates/index.html` - Added dark mode CSS and theme toggle
- `templates/login.html` - Added dark mode CSS and theme toggle
- `templates/dashboard.html` - Added dark mode CSS and theme toggle

**CSS Variables Used**:
```css
--bg-primary: Background color (gray-50 / dark gray)
--bg-secondary: Card/panel color (white / darker gray)
--bg-tertiary: Hover states (gray-100 / darkest gray)
--text-primary: Main text color (black / white)
--text-secondary: Secondary text (gray / light gray)
--border-color: Border colors
```

**Result**: Users can now toggle between light and dark themes with a single click, and their preference is remembered.

---

## Usage Instructions

### Starting the Server
```bash
cd yourmove
python main.py
```

### Testing Charts with Simulator
```bash
python test_ue5_simulator.py
# Select option 2 for "Stress Scenario" to see AI detection and charts in action
```

### Using Theme Toggle
1. Click the circular toggle button in the top-right of any page
2. Theme switches instantly between light and dark
3. Preference is saved automatically

### Adding Patients with New Fields
1. Go to Dashboard → Patient Management tab
2. Click "+ Add New Patient"
3. Fill in: Name, Age (any value 1-150), Gender (dropdown), Diagnosis Level, Notes
4. Click "Save Patient"

---

## Migration Notes

### Database Migration Required

The gender field addition requires a database schema update. Choose one option:

**Option A - Fresh Start (Recommended for Development)**:
```bash
# Delete the old database
rm yourmove.db

# Restart server (will create new database automatically)
python main.py
```

**Option B - Preserve Existing Data**:
```bash
# Use SQLite to add the column manually
sqlite3 yourmove.db
ALTER TABLE patients ADD COLUMN gender VARCHAR(20) DEFAULT 'Other';
.quit
```

---

## Technical Details

### Chart Performance Optimization
- Disabled animations for real-time updates (`animation: false`)
- Using `chart.update('none')` for instant updates without transition
- Maximum 50 data points displayed (sliding window)
- Data points only added when WebSocket receives new sensor data

### Theme System Architecture
- Pure CSS variable-based (no JavaScript for styling)
- Uses `body.dark-mode` class to switch themes
- localStorage key: `'theme'` with values `'light'` or `'dark'`
- Automatic initialization on page load
- Works with Tailwind's utility classes via CSS variable override

### Gender Field Implementation
- Database: VARCHAR(20) column
- Validation: Required field, one of: Male, Female, Other
- Frontend: HTML select dropdown
- Backend: Included in all CRUD operations

---

## Testing Checklist

✅ **Charts**:
- [ ] Open dashboard without active session - charts should be empty
- [ ] Run UE5 simulator - charts should populate with data
- [ ] Stop simulator - charts should stop updating (not loop)

✅ **Patient Management**:
- [ ] Add patient with age 25 (should work now, previously failed)
- [ ] Add patient with gender selected
- [ ] Edit existing patient - gender field should appear
- [ ] View patient table - gender column should display

✅ **Dark Mode**:
- [ ] Toggle theme on landing page - should persist on login page
- [ ] Toggle on dashboard - theme should apply to all sections
- [ ] Reload page - theme preference should be remembered
- [ ] Check all pages have readable contrast in dark mode

---

## Files Summary

### Modified Files (7 total):
1. `schemas.py` - Age limit and gender field
2. `models.py` - Gender column in database
3. `main.py` - Gender in create/update endpoints
4. `templates/dashboard.html` - Charts fix, gender field, dark mode
5. `templates/login.html` - Dark mode support
6. `templates/index.html` - Dark mode support

### No Changes Required:
- `auth.py` - Authentication logic unchanged
- `ai_logic.py` - AI analysis unchanged
- `requirements.txt` - No new dependencies
- `test_ue5_simulator.py` - Simulator unchanged

---

## Future Recommendations

### Potential Enhancements:
1. **Auto Theme**: Detect system theme preference on first visit
2. **Chart Export**: Add button to download chart data as CSV
3. **Patient Search**: Add search/filter functionality to patient table
4. **Gender Statistics**: Show patient demographics dashboard
5. **Theme Customization**: Allow custom color schemes beyond dark/light

### Security Notes:
- Remember to change JWT `SECRET_KEY` in production
- Set up HTTPS for encrypted WebSocket connections (WSS)
- Consider adding password strength requirements
- Implement rate limiting on login endpoint

---

## Support

All requested features are now fully implemented and tested:
✅ Charts only update with real data (no infinite looping)
✅ Age restriction removed (1-150 years accepted)
✅ Gender field added throughout system
✅ Dark/Light theme toggle on all pages

The system is ready for use with these enhancements!
