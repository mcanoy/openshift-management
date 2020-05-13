import os
import json
import requests
import datetime
import logging
import math

currentTime = datetime.datetime.now()

logging.basicConfig(level="INFO")
logger = logging.getLogger("com.redhat.labs")
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

git_base_url = os.environ.get('GITLAB_API_URL')
git_token = os.environ.get('GIT_TOKEN')
parent_group = os.environ.get('PARENT_GROUP_ID')
delete_after_hours_string = os.environ.get('DELETE_AFTER_HOURS')
delete_after_hours = 2147483647 # default but line above must be set and is enforced
dry_run = os.environ.get('DRY_RUN').lower() == 'true'

def check_env_vars():
    if parent_group is None:
        raise ValueError('OMP Parent Group (PARENT_GROUP_ID) is required')
    if not parent_group.isnumeric():
        raise ValueError('OMP Parent Group (PARENT_GROUP_ID) has an invalid value of ' + parent_group)
    if not git_token:
        raise ValueError('Git Token (GIT_TOKEN) is required')
    if not git_base_url:
        raise ValueError('Git Url base url (GITLAB_API_URL) is required (eg. https://gitlab.com)')
    if not delete_after_hours_string:
        raise ValueError('You must set a time period to delete projects (DELETE_AFTER_HOURS)')
    if not delete_after_hours_string.isnumeric():
        raise ValueError('You must set a time period to delete projects (DELETE_AFTER_HOURS)')

def get_groups(group_id):
    response = requests.get(
        git_base_url + '/groups/' + str(group_id) + '/subgroups',
        headers={"PRIVATE-TOKEN": git_token, 'Content-Type': 'application/json'},
    )

    if response.status_code == 200:
        return json.loads(response.text);
    if response.status_code == 401:
        raise ValueError('Git Token is not valid')

    return []
# end get_groups

# projects should only have 1 by automation but comes back as a list
def get_projects(group_id):
    deleted = True

    response = requests.get(
        git_base_url + '/groups/' + str(group_id)+ '/projects',
        headers={"PRIVATE-TOKEN": git_token, 'Content-Type': 'application/json'},
    )
    projects = json.loads(response.text)

    for project in projects:
        logger.debug(project['path_with_namespace'])
        lastActivity = datetime.datetime.strptime(project['last_activity_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
        logger.debug(f"Last Activity {lastActivity:%b %d %Y}")
        passedTime = currentTime - lastActivity
        elapsed_hours = passedTime.total_seconds() / 3600
        logger.debug(f"Delete? { elapsed_hours > delete_after_hours } :: Hours { int(elapsed_hours) }")
        if elapsed_hours < delete_after_hours:
            logger.debug(f"Found a recent repo for the engagment. No delete. Not empty { project['namespace']['name']}")
            deleted = False
        else:
            logger.info(f"Stale repository found. Last Activity {lastActivity:%b %d %Y}")

    return deleted

# end get_projects

def delete_group(group_id):
    logger.info(f"deleting group {group_id} dry run? {dry_run}")
    if not dry_run:
        response = requests.delete(
            git_base_url + '/groups/' + str(group_id),
            headers={"PRIVATE-TOKEN": git_token},
        )
        logger.debug("delete response code {response.status_code}")
        if response.status_code == 202 :
            logger.warn(f"deleted engagement {group_id}")
        else:
            logger.error(f"Failed to delete engagement {group_id} code {response.status}")


# end delete_group

check_env_vars()

git_base_url += '/api/v4'
if(dry_run):
   logger.info('In dry-run mode. No deletes will occur') 

delete_after_hours = int(delete_after_hours_string)
logger.info("Delete projects after %i hours", delete_after_hours)

customers = get_groups(parent_group);

for customer in customers:
    engagements = get_groups(customer['id'])

    logger.debug(f"Engagements for {customer['name']} = {len(engagements)}")
    counter = 0
    for engagement in engagements:
        ready_for_delete = get_projects(engagement['id'])
        
        if(ready_for_delete):
            delete_group(engagement['id'])
            counter += 1
    
    if(counter == len(engagements)):
        logger.info(f"All engagements were deleted for customer {customer['name']}")
        delete_group(customer['id'])

logger.info("Gitlab clean up complete")



