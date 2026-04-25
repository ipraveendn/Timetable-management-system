import openpyxl
import os

file_path = '/home/rushi/project/data/large_test_data.xlsx'
wb = openpyxl.load_workbook(file_path)
sheet = wb['Faculty']

# New row data
# ['Name', 'Employee ID', 'Subjects', 'Semesters', 'Max Classes Per Day', 'Available Days', 'Department', 'Email']
new_row = [
    'redev', 
    'EMP_REDEV_001', 
    'Computer Science, AI, Web Dev', 
    '1,2,3,4,5,6,7,8', 
    5, 
    'Monday, Tuesday, Wednesday, Thursday, Friday, Saturday', 
    'Computer Science', 
    'mounishmuniraju0228@gmail.com'
]

sheet.append(new_row)
wb.save(file_path)
print(f"Successfully added {new_row[0]} to {file_path}")
