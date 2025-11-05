import sqlglot
from sqlglot import exp

# Debug ALTER TABLE
ddl = '''
CREATE TABLE departments (
    dept_id INT AUTO_INCREMENT PRIMARY KEY,
    manager_id INT NULL
);

CREATE TABLE employees (
    emp_id INT AUTO_INCREMENT PRIMARY KEY
);

ALTER TABLE departments 
ADD CONSTRAINT fk_dept_manager 
FOREIGN KEY (manager_id) REFERENCES employees(emp_id);
'''

parsed = sqlglot.parse(ddl, dialect='mysql')
for stmt in parsed:
    print(f'Statement: {type(stmt).__name__}')
    if isinstance(stmt, exp.Alter):
        print(f'  Table: {stmt.this.name}')
        print(f'  Actions: {stmt.actions}')
        for action in stmt.actions:
            print(f'    Action type: {type(action).__name__}')
            if isinstance(action, exp.AddConstraint):
                print(f'      Constraint: {type(action.this).__name__}')
                print(f'      Full: {action.this}')
