![Gitlab Delete Projects Container](https://github.com/mcanoy/openshift-management/workflows/Gitlab%20Delete%20Projects%20Container/badge.svg)

# Gitlab Delete Projects Job

A cronjob that enables OpenShift to delete Gitlab projects that have become stale by checking the age of a repo. Thiis also deletes groups that have no projects. 

**Caution:** this jobs performs hard deletes. The actual deletion policy is influenced by overarching settings in Gitlab.
