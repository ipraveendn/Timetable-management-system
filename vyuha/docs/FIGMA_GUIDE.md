# Figma Design Guide for VYUHA

## Quick Start (5 minutes)

### Step 1: Create Figma Account
1. Go to [figma.com](https://figma.com)
2. Sign up for free
3. Click "New Design File"

### Step 2: Set Up Your Design System
From `figma-design-specs.json`, use these exact values:

**Colors (add to Styles):**
- Primary: `#007bff`
- Secondary: `#6c757d`  
- Background: `#f8f9fa`
- Surface: `#ffffff`
- Success: `#28a745`
- Warning: `#ffc107`
- Danger: `#dc3545`

**Typography:**
- Font: Inter
- Base size: 14px

### Step 3: Design These 4 Screens

#### 1. Login Screen
- Centered card on light background
- Logo: "VYUHA"
- Tagline: "AI-Powered Timetable & Substitution System"
- Email input with icon
- Password input with eye toggle
- Primary "Sign In" button (full width)
- "Forgot Password?" link
- "Register New College" secondary button

#### 2. Dashboard
**Left Sidebar (240px width):**
- Logo at top
- Navigation items with icons:
  - Timetable (active)
  - Upload Excel
  - Chat Assistant
  - Faculty
  - Reports
  - Settings

**Main Content:**
- Header: "Welcome back, Admin"
- 3 stat cards:
  - Total Faculty: 45
  - Active Classes: 68
  - Pending Leaves: 3
- Action buttons: "Generate Timetable", "View Substitutions"
- Weekly schedule preview

#### 3. Timetable Editor
**Toolbar:**
- Semester dropdown
- Day dropdown
- "Auto-Generate" button (blue)
- "Save" button (green)
- "Export" button (gray)

**Grid:**
- 7 columns: Time, Mon, Tue, Wed, Thu, Fri, Sat
- 9 time slots: 08:00 to 17:00
- Each cell shows: Subject, Faculty, Room
- Empty cells have "+" icon

#### 4. Chat Interface
**Left Sidebar:**
- "Recent Conversations" section
- "Quick Actions" buttons

**Chat Area:**
- Messages (user right, AI left)
- AI message has:
  - Avatar
  - Suggested substitutes with [Confirm] [Reject] buttons
- Input box at bottom with send button

### Step 4: Export for Development
1. Select frame
2. Right-click → "Copy as PNG" or "Copy as CSS"
3. Or use Dev Mode (blue button) to get React code

## College ID Setup

### Option 1: Mock Login (Quick)
Use hardcoded `college_id: "COLLEGE_001"` for testing

### Option 2: Real Login with Supabase
When user logs in, store their `college_id` and pass it in API headers:
```javascript
headers: {
  'X-College-ID': user.college_id
}
```

## Next Steps
1. Create Figma file
2. Share the link with your team
3. Once design is approved, implement in React
4. Connect to backend API with college_id

**Need help with specific Figma features?** Ask and I'll guide you!