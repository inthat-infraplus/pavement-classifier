# Pavement Classifier - User Guide

## Overview
This application is a FastAPI-based web system for classifying pavement images. It uses a two-tier user role system:
- **L1 Users (Admin/Managers)**: Create L2 users, assign tasks with file paths, and review classifications
- **L2 Users (Workers)**: Classify images from assigned folders and complete tasks

---

## How to Assign File Paths to L2 Users

### Step 1: L1 User Logs In
1. Start the application
2. Navigate to the login page
3. Log in with your L1 credentials

### Step 2: Create L2 User (if needed)
1. Go to the **L1 Dashboard**
2. In the "Create L2 User" section, enter:
   - **Username**: Name for the L2 user
   - **Password**: Password for the L2 user
3. Click "Create L2 User"

### Step 3: Assign Task with File Path
1. On the **L1 Dashboard**, find the "Create Task" section
2. Fill in:
   - **Folder Path**: Full path to the survey data folder
     - **Example**: `E:\S25_DRR\xeno\survey_data_20250504\PAVE\20250504_1\PAVE-0`
     - **Note**: Path must be accessible from the server machine
   - **Assignee**: Select the L2 user from the dropdown
3. Click "Create Task"

### Step 4: System Automatically Scans Images
- The system automatically scans the folder for supported image formats:
  - `.jpg`, `.jpeg`, `.png`, `.bmp`
- Each image is registered as a classification task
- The L2 user will see these images in their dashboard

### Step 5: L2 User Accesses Their Tasks
1. L2 user logs in
2. Views **L2 Dashboard** showing all assigned tasks
3. Clicks on a task to start classifying images
4. For each image, selects one of:
   - **Pavement**: If the image shows pavement
   - **Normal**: If the image shows other surfaces
5. Task is marked as "completed" when all images are classified

---

## Complete Workflow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     L1 USER WORKFLOW                         │
├─────────────────────────────────────────────────────────────┤
│ 1. Login to L1 Dashboard                                     │
│ 2. Create L2 User (username + password)                      │
│ 3. Assign Task:                                              │
│    - Select folder path (e.g., E:\PAVE\20250504_1\PAVE-0)  │
│    - Select L2 assignee                                      │
│ 4. System scans folder for images                            │
│ 5. View QC Check reports                                     │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                     L2 USER WORKFLOW                         │
├─────────────────────────────────────────────────────────────┤
│ 1. Login to L2 Dashboard                                     │
│ 2. View assigned tasks with folder paths                     │
│ 3. Click on task to start classifying                        │
│ 4. Classify each image as:                                   │
│    - "Pavement" or "Normal"                                  │
│ 5. Task auto-completes when all images classified            │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                 L1 USER QC CHECK WORKFLOW                    │
├─────────────────────────────────────────────────────────────┤
│ 1. View completed tasks                                      │
│ 2. Review all classifications in QC Check view               │
│ 3. Approve or modify classifications if needed               │
└─────────────────────────────────────────────────────────────┘
```

---

## Example: Assigning Path `E:\S25_DRR\xeno\survey_data_20250504\PAVE\20250504_1\PAVE-0`

### Prerequisites
- L1 user must be logged in
- L2 user must already be created
- The path `E:\S25_DRR\xeno\survey_data_20250504\PAVE\20250504_1\PAVE-0` must:
  - Be accessible from the server machine
  - Contain supported image files (`.jpg`, `.jpeg`, `.png`, `.bmp`)

### Steps
1. **Navigate to L1 Dashboard** → "Create Task" section
2. **Folder Path field**: Paste exactly:
   ```
   E:\S25_DRR\xeno\survey_data_20250504\PAVE\20250504_1\PAVE-0
   ```
3. **Assignee field**: Select the L2 user who will classify images from this folder
4. **Click**: "Create Task" button

### Result
- Task is created with status "pending"
- All images in the folder are automatically registered
- L2 user sees this task in their dashboard
- L2 user can immediately start classifying images

---

## System Architecture

### Database Models

#### User
- `id` (Primary Key)
- `username` (Unique)
- `role` (L1 or L2)
- `hashed_password`

#### Task
- `id` (Primary Key)
- `assigner_id` (Foreign Key → User, L1 user who created task)
- `assignee_id` (Foreign Key → User, L2 user assigned to task)
- **`folder_path`** (Path to survey data folder)
- `status` (pending or completed)
- `created_at` (Timestamp)

#### Image
- `id` (Primary Key)
- `task_id` (Foreign Key → Task)
- `filename` (Image file name)
- `label` (pavement, normal, or null if unclassified)

### File Serving
- When L2 user classifies an image, it's served from: `{task.folder_path}/{image.filename}`
- System validates that L2 user only accesses images from their assigned tasks
- Files are served directly from the disk using `FileResponse`

---

## Important Notes

### Path Requirements
- **Absolute paths** must be used (e.g., `E:\S25_DRR\...` not relative paths)
- **Path must be accessible** from the server running the application
- **Network paths** are supported if properly mapped (e.g., `\\server\share\path`)
- **Special characters**: Windows paths are supported as-is

### Image Support
- Supported formats: `.jpg`, `.jpeg`, `.png`, `.bmp`
- **Case-insensitive** extension matching
- Other image formats (`.gif`, `.tiff`, etc.) are ignored
- Non-image files in the folder are ignored

### Security
- L2 users can **only** access images from their assigned tasks
- L2 users cannot:
  - Create tasks
  - Create other users
  - Access images from other users' tasks
  - Access the QC Check view
- L1 users have full access to all tasks and QC operations

### Performance
- Image scanning happens **once** when task is created
- Large folders (1000+ images) may take a few seconds to scan
- All image metadata is stored in database for fast retrieval

---

## Troubleshooting

### "Invalid folder path" error
- ✓ Check path exists and is accessible from the server machine
- ✓ Verify path uses correct separators (`\` for Windows, `/` for network paths)
- ✓ Ensure no special permissions are blocking access

### Task created but no images appear
- ✓ Check folder contains supported image formats (.jpg, .png, .bmp, .jpeg)
- ✓ Verify files are not corrupted or named with unusual characters
- ✓ Check file permissions allow reading by the application

### L2 user cannot see assigned task
- ✓ Verify task was created with correct `assignee_id`
- ✓ Refresh the L2 Dashboard page
- ✓ Check user role is set to "L2" in database

### Cannot access image file
- ✓ Verify original folder path still exists and is accessible
- ✓ Verify file has not been moved or deleted
- ✓ Check file permissions allow read access

---

## Docker Deployment

### Building and Running
```bash
# Build images
docker compose build

# Start services
docker compose up -d

# Stop services
docker compose down
```

### Environment Configuration
- Database: SQLite (default) or configure in `app/db.py`
- Server port: Configure in docker-compose.yml
- File paths: Must be accessible from Docker container (use mounted volumes or network paths)

---

## Technology Stack
- **Backend**: FastAPI (Python)
- **Database**: SQLAlchemy ORM (SQLite by default)
- **Frontend**: Jinja2 Templates + HTML/CSS
- **Authentication**: Cookie-based sessions with bcrypt password hashing
- **Image Serving**: FastAPI FileResponse

---

## API Endpoints

### Authentication
- `GET /login` - Login page
- `POST /login` - Submit login credentials
- `GET /logout` - Logout user

### L1 User Endpoints
- `GET /l1_dashboard` - View L1 dashboard
- `POST /users/create_l2` - Create new L2 user
- `POST /tasks` - Create new task with folder path and assignee
- `GET /tasks/{task_id}/qc` - View QC check for a task
- `POST /api/images/{image_id}/qc_update` - Update classification in QC

### L2 User Endpoints
- `GET /l2_dashboard` - View assigned tasks
- `GET /tasks/{task_id}/classify` - View classification interface
- `POST /api/images/{image_id}/classify` - Submit image classification
- `GET /api/images/serve/{image_id}` - Get image file

---

## Support & Future Enhancements

### Potential Improvements
- [ ] Batch path assignment for multiple folders
- [ ] Path templates for common survey data structures
- [ ] Task deadline/priority management
- [ ] Image preview/zoom functionality
- [ ] Detailed progress reporting
- [ ] Export classification results to CSV/JSON
- [ ] User activity audit log

### Questions?
Refer to the technical architecture section above or contact the system administrator.
