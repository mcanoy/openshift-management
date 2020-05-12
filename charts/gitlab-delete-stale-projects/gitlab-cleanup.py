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
delete_after_hours = 2147483647
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
    delete_after_hours = int(delete_after_hours_string)

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
        createTime = datetime.datetime.strptime(project['created_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
        logger.debug("created " + createTime.strftime("%b %d %Y"))
        passedTime = currentTime - createTime
        elapsed_hours = passedTime.total_seconds() / 3600
        logger.debug("Delete? " +  str(elapsed_hours > delete_after_hours) + " :: Hours " + str(int((elapsed_hours))))
        if elapsed_hours < delete_after_hours:
            logger.debug("Found a recent repo in the residency. Don't delete residency. Not empty " + project['path_with_namespace'])
            deleted = False

    return deleted

# end get_projects

def delete_group(group_id):
    logger.info("deleting group " + str(group_id) + " dry run? " + str(dry_run));
    if not dry_run:
        response = requests.delete(
            git_base_url + '/groups/' + str(group_id),
            headers={"PRIVATE-TOKEN": git_token},
        )
        logger.info(response.status_code)
        if response.status_code == 202 :
            logger.warn("deleted residency " + str(group_id));
        else:
            logger.error("Failed to delete residency " + str(group_id) + " code " + str(response.status))


# end delete_group

check_env_vars()
git_base_url += '/api/v4'
if(dry_run):
   logger.info('In dry-run mode. No deletes will occur') 

logger.info("Delete projects after %i hours", delete_after_hours)

customers = get_groups(parent_group);

for customer in customers:
    logger.debug("customer " + str(customer['id']))
    residencies = get_groups(customer['id'])

    logger.debug(len(residencies))
    counter = 0
    for residency in residencies:
        ready_for_delete = get_projects(residency['id'])
        
        if(ready_for_delete):
            delete_group(residency['id'])
            counter += 1
    
    if(counter == len(residencies)):
        logger.info("All residencies were deleted for customer " + customer['name'])
        delete_group(customer['id'])

logger.info("Gitlab clean up complete")
#"2020-04-15T22:52:10.606Z"
#"%Y-%m-%dT%H:%M:%S.fZ"



