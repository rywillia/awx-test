"""Awx evaluation module."""
import json

import os
from tower_cli import get_resource
from tower_cli.exceptions import Found, NotFound


# TODO: Add in additional parameters that are optional for all methods.


class AwxBase(object):
    __resource_name__ = None

    @property
    def name(self):
        """Return resource name."""
        return self.__resource_name__

    @property
    def resource(self):
        """Return resource class object."""
        return get_resource(self.name)

    @property
    def organization(self):
        """Return organization class instance."""
        return AwxOrganization()

    @property
    def inventory(self):
        """Return inventory class instance."""
        return AwxInventory()

    @property
    def credential(self):
        """Return credential class instance."""
        return AwxCredential()


class AwxAdHoc(AwxBase):
    """Awx ad hoc class."""
    __resource_name__ = 'ad_hoc'

    def __init__(self):
        """Constructor."""
        super(AwxAdHoc, self).__init__()

    @property
    def ad_hocs(self):
        """Return list of ad hocs."""
        return self.resource.list()

    def launch(self, job_type, module, inventory, credential):
        """Launch a ad hoc command.

        :param job_type: Job type field.
        :type job_type: str
        :param module: Module name.
        :type module: str
        :param inventory: Inventory field.
        :type inventory: str
        :param credential: Credential field.
        :type credential: str
        :return: Launch data
        :rtype: dict
        """
        # get credential object
        _credential = self.credential.get(credential)

        # get inventory object
        _inventory = self.inventory.get(inventory)

        return self.resource.launch(
            job_type=job_type,
            module_name=module,
            inventory=_inventory['id'],
            credential=_credential['id']
        )


class AwxConfig(AwxBase):
    __resource_name__ = 'config'

    def __init__(self):
        super(AwxConfig, self).__init__()


class AwxCredential(AwxBase):
    """Awx credential class."""
    __resource_name__ = 'credential'

    def __init__(self):
        """Constructor."""
        super(AwxCredential, self).__init__()

    @property
    def credentials(self):
        """Return list of credentials."""
        return self.resource.list()

    def create(self, name, kind, organization, **kwargs):
        """Create a credential entry.

        :param name: Credential name.
        :type name: str
        :param kind: Credential type.
        :type kind: str
        :param organization: Organization name.
        :type organization: str
        :param kwargs: key=value data for optional arguments.
        :type dict
        """
        supported_kinds = ['ssh']

        # quit if kind not supported
        if kind not in supported_kinds:
            raise Exception('Kind %s is invalid.' % kind)

        # check if organization exists
        _org = self.organization.get(organization)

        # quit if organization not found
        if not _org:
            raise Exception('Organization %s not found.' % organization)

        # call method for credential support
        getattr(self, '_create_%s_kind' % kind)(
            name,
            kind,
            _org,
            kwargs
        )

    def _create_ssh_kind(self, name, kind, organization, kwargs):
        """Create a SSH credential entry.

        :param name: Credential name.
        :type name: str
        :param kind: Credential type.
        :type kind: str
        :param organization: Organization name.
        :type organization: str
        :param kwargs: key=value data for optional arguments.
        :type dict
        """
        key = 'ssh_key_data'

        # quit if required key not defined
        if key not in kwargs:
            raise Exception('Kwargs requires %s.' % key)

        # check if ssh private key exists
        if not os.path.exists(kwargs['ssh_key_data']):
            raise Exception('SSH private key %s not located.' % key)

        # load ssh private key
        with open(kwargs[key], 'r') as fh:
            key_content = fh.read()

        # create credential entry
        self.resource.create(
            name=name,
            kind=kind,
            organization=organization['id'],
            ssh_key_data=key_content
        )

    def delete(self, name, kind):
        """Delete a credential entry."""
        self.resource.delete(name=name, kind=kind)

    def get(self, name):
        """Get credential.

        :param name: Credential name.
        :type name: str
        :return: Credential object.
        :type dict
        """
        try:
            return self.resource.get(name=name)
        except NotFound as ex:
            raise Exception(ex.message)


class AwxGroup(AwxBase):
    __resource_name__ = 'group'

    def __init__(self):
        super(AwxGroup, self).__init__()


class AwxHost(AwxBase):
    """Awx host class."""
    __resource_name__ = 'host'

    def __init__(self):
        """Constructor."""
        super(AwxHost, self).__init__()

    @property
    def hosts(self):
        """Return list of hosts."""
        return self.resource.list()

    def create(self, name, inventory, variables=None):
        """Create a host."""
        # check if inventory exists
        try:
            _inv = self.inventory.get(inventory)
        except Exception:
            raise Exception('Inventory %s not found.' % inventory)

        self.resource.create(
            name=name,
            inventory=_inv['id'],
            variables=json.dumps(variables)
        )

    def delete(self, name, inventory):
        """Delete a host."""
        # check if inventory exists
        try:
            _inv = self.inventory.get(inventory)
        except Exception:
            raise Exception('Inventory %s not found.' % inventory)

        self.resource.delete(
            name=name,
            inventory=_inv['id']
        )


class AwxInventory(AwxBase):
    """Awx inventory class."""
    __resource_name__ = 'inventory'

    def __init__(self):
        """Constructor."""
        super(AwxInventory, self).__init__()

    @property
    def inventories(self):
        """Return list of inventories."""
        return self.resource.list()

    def create(self, name, organization, description=None, variables=None):
        """Create an inventory file.

        :param name: Filename.
        :type name: str
        :param organization: Organization name.
        :type organization: str
        :param description: Inventory description.
        :type description: str
        :param variables: Inventory variables.
        :type variables: dict
        """
        # check if organization exists
        _org = self.organization.get(organization)

        # quit if organization not found
        if not _org:
            raise Exception('Organization %s not found.' % organization)

        try:
            self.resource.create(
                name=name,
                organization=_org['id'],
                description=description,
                variables=variables,
                fail_on_found=True
            )
        except Found as ex:
            raise Exception(ex.message)

    def delete(self, name):
        """Delete an inventory.

        :param name: Filename.
        :type name: str
        """
        self.resource.delete(name=name)

    def get(self, name):
        """Get inventory.

        :param name: Inventory name.
        :type name: str
        :return: Inventory object.
        :rtype: dict
        """
        try:
            return self.resource.get(name=name)
        except NotFound as ex:
            raise Exception(ex.message)


class AwxInventoryScript(AwxBase):
    __resource_name__ = 'inventory_script'

    def __init__(self):
        super(AwxInventoryScript, self).__init__()


class AwxJob(AwxBase):
    __resource_name__ = 'job'

    def __init__(self):
        super(AwxJob, self).__init__()


class AwxJobTemplate(AwxBase):
    __resource_name__ = 'job_template'

    def __init__(self):
        super(AwxJobTemplate, self).__init__()


class AwxLabel(AwxBase):
    __resource_name__ = 'label'

    def __init__(self):
        super(AwxLabel, self).__init__()


class AwxNode(AwxBase):
    __resource_name__ = 'node'

    def __init__(self):
        super(AwxNode, self).__init__()


class AwxNotificationTemplate(AwxBase):
    __resource_name__ = 'notification_template'

    def __init__(self):
        super(AwxNotificationTemplate, self).__init__()


class AwxOrganization(AwxBase):
    """Awx organization class."""
    __resource_name__ = 'organization'

    def __init__(self):
        """Constructor."""
        super(AwxOrganization, self).__init__()

    @property
    def organizations(self):
        """Return list of organizations."""
        return self.resource.list()

    def create(self, name, description=None):
        """Create an organization.

        :param name: Organization name.
        :type name: str
        :param description: Organization description.
        :type description: str
        """
        try:
            self.resource.create(
                name=name,
                description=description,
                fail_on_found=True
            )
        except Found as ex:
            raise Exception(ex.message)

    def delete(self, name):
        """Delete an organization.

        :param name: Organization name.
        :type name: str
        """
        self.resource.delete(name=name)

    def get(self, name):
        """Get organization.

        :param name: Organization name.
        :type name: str
        :return: Organization object.
        :rtype: dict
        """
        for item in self.organizations['results']:
            if item['name'] == name:
                return item
        return {}


class AwxPermission(AwxBase):
    __resource_name__ = 'permission'

    def __init__(self):
        super(AwxPermission, self).__init__()


class AwxProject(AwxBase):
    __resource_name__ = 'project'

    def __init__(self):
        super(AwxProject, self).__init__()


class AwxRole(AwxBase):
    __resource_name__ = 'role'

    def __init__(self):
        super(AwxRole, self).__init__()


class AwxSchedule(AwxBase):
    __resource_name__ = 'schedule'

    def __init__(self):
        super(AwxSchedule, self).__init__()


class AwxSetting(AwxBase):
    __resource_name__ = 'setting'

    def __init__(self):
        super(AwxSetting, self).__init__()


class AwxTeam(AwxBase):
    __resource_name__ = 'team'

    def __init__(self):
        super(AwxTeam, self).__init__()


class AwxUser(AwxBase):
    __resource_name__ = 'user'

    def __init__(self):
        super(AwxUser, self).__init__()


class AwxVersion(AwxBase):
    __resource_name__ = 'version'

    def __init__(self):
        super(AwxVersion, self).__init__()


class AwxWorkflow(AwxBase):
    __resource_name__ = 'workflow'

    def __init__(self):
        super(AwxWorkflow, self).__init__()


class AwxWorkflowJob(AwxBase):
    __resource_name__ = 'workflow_job'

    def __init__(self):
        super(AwxWorkflowJob, self).__init__()
