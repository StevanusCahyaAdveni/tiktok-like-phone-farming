import sys

with open('tiktok_auto_lab_cloneApp.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
in_worker = False

for line in lines:
    if 'def device_worker_thread' in line:
        in_worker = True
        new_lines.append(line)
        new_lines.append('        class StopAutomationException(Exception): pass\n')
        new_lines.append('        def smart_sleep(seconds):\n')
        new_lines.append('            import time as t\n')
        new_lines.append('            end = t.time() + seconds\n')
        new_lines.append('            while t.time() < end:\n')
        new_lines.append('                if not self.is_running:\n')
        new_lines.append('                    raise StopAutomationException()\n')
        new_lines.append('                t.sleep(0.5)\n')
        continue
    
    if in_worker and 'for clone_num in range' in line:
        new_lines.append('        try:\n')
        new_lines.append('    ' + line)
        continue
        
    if in_worker and 'self.logger.log(f"[{device_id}] Worker Thread finished execution lifecycle.")' in line:
        new_lines.append('    ' + line)
        new_lines.append('        except StopAutomationException:\n')
        new_lines.append('            self.logger.log(f"[{device_id}] \u23F9 EMERGENCY STOP: Worker thread forcefully halted!")\n')
        in_worker = False
        continue

    if in_worker and 'time.sleep(' in line and 'smart_sleep' not in line:
        line = line.replace('time.sleep(', 'smart_sleep(')
        
    if in_worker and line.startswith('        ') and 'class StopAutomation' not in line and 'def smart_sleep' not in line and not line.strip().startswith('try:'):
        # We need to indent everything that was originally at 2 indents (8 spaces) to 3 indents (12 spaces)
        # Because we wrapped the `for` loop in a `try:` block!
        # Wait, the `for` loop itself was at 8 spaces. `try:` is at 8 spaces.
        # So EVERYTHING from the `for` loop onwards needs +4 spaces.
        pass
        
    # Better approach for indentation:
    if in_worker and line.startswith('        ') and 'for clone_num in range' not in line and not line.strip() == '':
        pass

# It's actually easier to just manually write the block since it's only 140 lines!
