import yaml
import os
import uuid
import time
from awx import Awx


class Run(object):

    __organization__ = 'Carbon'

    def __init__(self, input_config, tower_config):
        self.tower_config = tower_config
        self.hosts = input_config['provision']
        self.orchestrate = input_config['orchestrate']
        self.rid = uuid.uuid4().hex[:4]

        self.inventory = 'inventory_%s' % self.rid
        self.project = 'project_%s' % self.rid

        self.awx = Awx(
            self.tower_config['host'],
            self.tower_config['username'],
            self.tower_config['password']
        )

    @property
    def organization(self):
        return self.__organization__

    def go(self):
        # create inventory
        self.awx.inventory.create(self.inventory, self.organization)

        # add hosts
        for host in self.hosts:
            try:
                ssh_key = host['ansible_vars'].\
                    pop('ansible_ssh_private_key_file')
            except KeyError:
                raise Exception('ansible_ssh_private_key_file key not found!')

            # create host
            self.awx.host.create(
                host['host'],
                self.inventory,
                host['ansible_vars']
            )

            # create credential
            credential = 'credential_%s' % self.rid
            self.awx.credential.create_ssh_credential(
                credential,
                self.organization,
                ssh_key
            )

        for item in self.orchestrate:
            # create project
            try:
                project = item['scm']['url'].split('/')[-1].split('.')[0]

                self.awx.project.create_scm_project(
                    project,
                    item['scm']['url'],
                    self.organization,
                    'git',
                    url=item['scm']['url']
                )
            except Exception:
                self.awx.logger.warn('Project %s already exists.' % project)

            # lets delay for SCM update to finish
            # TODO: add a better check here
            self.awx.logger.warn('Delay 15 seconds for SCM update to finish.')
            time.sleep(15)

            # create job template
            job_template = 'job_%s' % self.rid
            self.awx.job_template.create(
                job_template,
                item['description'],
                'run',
                self.inventory,
                project,
                '%s.yml' % item['name'],  # TODO: which file ext?
                credential
            )

            # run job template
            results = self.awx.job.launch(
                job_template,
                item['description']
            )

            # wait for job to complete
            try:
                output = self.awx.job.monitor(
                    results['id'],
                    interval=1,
                    timeout=300
                )
                self.awx.logger.debug(output)
            except Exception as ex:
                self.awx.logger.warn(ex)

            # delete inventory
            self.awx.inventory.delete(self.inventory)

            # delete credential
            self.awx.credential.delete(credential, 'ssh')

            # delete job template
            self.awx.job_template.delete(job_template, project)

            # delete project
            self.awx.project.delete(project)


if __name__ == '__main__':
    # load yaml input
    with open('input.yml', 'r') as fh:
        config1 = yaml.load(fh)

    # tower config exist
    tower_cfg = '/etc/tower/tower_cli.cfg'
    if not os.path.isfile(tower_cfg):
        raise Exception('Req. configuration file %s is missing!' % tower_cfg)

    # load tower configuration file
    config2 = dict()
    with open(tower_cfg, 'r') as fh:
        for item in fh.readlines():
            val = item.split(':', 1)
            config2[val[0]] = val[1].strip()

    # create run object
    run = Run(config1, config2)

    # start
    run.go()
