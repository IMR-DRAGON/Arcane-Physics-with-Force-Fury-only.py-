import re

with open('battle_sim.py', 'r', encoding='utf-8') as f:
    c = f.read()

# Fix Ability(""name"", ...) to Ability("name", ...)
c = re.sub(r'Ability\(\s*\"\"([^\"]+)\"\"', r'Ability("\1"', c)

with open('battle_sim.py', 'w', encoding='utf-8') as f:
    f.write(c)

print('Syntax fixed.')
