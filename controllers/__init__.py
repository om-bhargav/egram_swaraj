from excel import get_pending_users
from panel import GPPanel
from panel.reconsilation import ReconsilationPanel
from panel.createnregister import CreateAndRegisterPlanPanel
from excel.reconsilation import get_reconciliation_users,update_reconciliation_remarks
from excel.createnregisterplan import get_users,mark_users_done
def process_panchayat_development_plan(config):
    users_with_records = get_pending_users(config)
    
    panel = GPPanel(config)
    
    for (username, password), records in users_with_records.items():
        panel.run(
            username=username,
            password=password,
            records=records,
        )

def process_reconsilation(config):
    try:
        users = get_reconciliation_users(config)
        panel = ReconsilationPanel(config)
        lst = []
        for (username,password),option in users.items():
            panel.run(username,password)
            lst.append((username,password))
    finally:
        update_reconciliation_remarks(config,lst)


def process_createnregisterplan(config):
    done = []
    try:
        users = get_users(config)
        panel = CreateAndRegisterPlanPanel(config)
        for (username,password),years in users.items():
            panel.run(username,password,years)
            done.append((username,password))
    finally:
        mark_users_done(config,done)