import openpyxl

file_path = '/home/rushi/project/data/large_test_data.xlsx'
wb = openpyxl.load_workbook(file_path)
sheet = wb['Faculty']

# Find the row for 'redev' and update its subjects
for row in sheet.iter_rows(min_row=2):
    if row[0].value == 'redev':
        # Update with actual codes from the 'Subjects' sheet
        row[2].value = 'CS108, CS202, CS601, CS804' 
        print(f"Updated redev with subjects: {row[2].value}")
        break

wb.save(file_path)
