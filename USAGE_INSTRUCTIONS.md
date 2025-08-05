# How to Use the Coupa Downloads Tool

## Step 1: Prepare Your PO Numbers
1. Open the file `data/input/input.csv`
2. Add your Purchase Order (PO) numbers in the first column
3. Save the file

**Example format:**
```
PO_NUMBER
PO15262984
PO15327452
PO15362783
```

## Step 2: Install Dependencies
1. Open Terminal/Command Prompt
2. Navigate to the project folder
3. Run: `pip install -r requirements.txt`

## Step 3: Run the Tool
1. In the same terminal, run: `python src/main.py`
2. The tool will automatically:
   - Open a web browser
   - Navigate to Coupa
   - Wait for you to log in manually (if needed)
   - Download attachments from each PO

## Step 4: Monitor Progress
- Watch the terminal for progress updates
- The tool will show which PO is being processed
- You'll see success/failure messages for each download

## Step 5: Find Your Downloads
- All downloaded files are saved to: `~/Downloads/CoupaDownloads/`
- Files are automatically renamed with the PO number as prefix
- Example: `PO15262984_filename.pdf`

## What the Tool Does
- Downloads PDF, MSG, and DOCX attachments from Coupa PO pages
- Automatically renames files with PO prefixes
- Handles login detection
- Processes multiple POs in batch
- Creates organized folders by supplier

## If Something Goes Wrong
- Check that your PO numbers are correct
- Ensure you have internet connection
- Make sure you're logged into Coupa
- Check the terminal for error messages

That's it! The tool handles everything else automatically. 