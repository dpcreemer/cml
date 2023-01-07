import requests
import json, yaml
from getpass import getpass

requests.packages.urllib3.disable_warnings()

def interface_name_split(name):
  digpos = [n for n in range(len(name)) if name[n].isdigit()]
  if not digpos: return (name, None)
  return (name[:digpos[0]], name[digpos[0]:])

class CML(object):
  def __init__(self, address, username=None, password=None, verify=False):
    self.__session = requests.Session()
    self.__address = None
    self.__username = None
    self.__password = None
    self.__token = None
    self.address = address
    self.username = username
    self.password = password
    self.verify = verify
  
  def __getattr__(self, attr):
    try:
      lab = self.get_labs_by_title(attr)[0]
    except:
      raise Exception(f"Object 'CML' has not attribute '{attr}'.")
    return lab

  @property
  def address(self):
    return self.__address
  
  @address.setter
  def address(self, address):
    if address[:4].lower() == 'http':
      address = address.split('//')[1]
    address = address.split('/')[0]
    self.__address = address
  
  @property
  def username(self):
    return self.__username

  @username.setter
  def username(self, username):
    self.__username = username
  
  @property
  def password(self):
    return None
  
  @password.setter
  def password(self, password):
    self.__password = password
  
  @property
  def labs(self):
    return self.get_labs()
  
  @property
  def node_definitions(self):
    return [Node_Definition(self, node_def['id']) for node_def in self.get("node_definitions")]
  
  @property
  def __headers(self):
    headers = {'accept': 'application/json'}
    if self.__token: headers['authorization'] = f'Bearer {self.__token}'
    return headers

  def __build_url(self, path, parameters=None):
    url = f"https://{self.address}/api/v0/{path}"
    parameters = self.__build_parameter_string(parameters)
    if parameters: url += "?" + parameters
    return url
  
  def __build_parameter_string(self, parameters):
    if not parameters or parameters == "": return None
    if type(parameters) is str:
      if parameters[:1] == "?": return parameters[1:]
      return parameters
    return "&".join([f"{key}={value}" for (key, value) in parameters.items()])

  def __get(self, path, parameters=None):
    url = self.__build_url(path, parameters)
    rsp = self.__session.get(url, headers=self.__headers, verify=self.verify)
    return rsp
  
  def __post(self, path, data):
    url = self.__build_url(path)
    if type(data) is dict: data = json.dumps(data)
    rsp = self.__session.post(url, data=data, headers=self.__headers, verify=self.verify)
    return rsp
  
  def __put(self, path):
    url = self.__build_url(path)
    rsp = self.__session.put(url, headers=self.__headers, verify=self.verify)
    return rsp
  
  def __patch(self, path, data):
    url = self.__build_url(path)
    if type(data) is dict: data = json.dumps(data)
    rsp = self.__session.patch(url, data=data, headers=self.__headers, verify=self.verify)
    return rsp
  
  def __delete(self, path):
    url = self.__build_url(path)
    rsp = self.__session.delete(url, headers=self.__headers, verify=self.verify)
    return rsp
  
  def get(self, path, parameters=None):
    rsp = self.__get(path, parameters)
    return rsp.json()
  
  def post(self, path, data):
    rsp = self.__post(path, data)
    if not rsp.ok: raise Exception(f"Post failed: {rsp.text}")
    return rsp.json()
  
  def put(self, path):
    rsp = self.__put(path)
    if not rsp.ok: raise Exception(f"Put failed: {rsp.text}")
  
  def patch(self, path, data):
    rsp = self.__patch(path, data)
    if not rsp.ok: raise Exception(f"Patch failed: {rsp.text}")
  
  def delete(self, path):
    rsp = self.__delete(path)
    if not rsp.ok: raise Exception(f"Delete failed: {rsp.text}")
  
  def login(self, username=None, password=None):
    if username is not None: self.username = username
    if password is not None: self.password = password
    if self.username is None: self.username = input("Username: ")
    if self.__password is None: self.password = getpass("Password: ")
    data = {
      'username': self.username,
      'password': self.__password
    }
    self.__token = None
    rsp = self.__post("authenticate", data)
    if not rsp.ok: 
      self.username = None
      self.password = None
      raise Exception(f"Login Failure: {rsp.text}")
    self.__token = rsp.json()
  
  def logout(self):
    self.delete('logout')
    self.username = None
    self.password = None
    self.__token = None
  
  def get_labs(self, show_all=True):
    labs = self.get("labs", {'show_all':show_all})
    return [Lab(self, lab) for lab in labs]
  
  def get_labs_by_title(self, title):
    return [lab for lab in self.labs if lab.title == title]
  
  def create_lab(self, title, description='', notes=''):
    data = {
      'title': title,
      'description': description,
      'notes': notes
    }
    rsp = self.__post('labs', data)
    return Lab(self, rsp.json()['id'])
  
  def get_node_definition_by_name(self, name):
    node_definition = [nd for nd in self.node_definitions if nd.name == name or nd.id == name][0]
    if not node_definition: raise Exception(f"Node Definition {name} not found.")
    return node_definition
  

###############################
###  Node Definition Object ###
###############################
class Node_Definition(object):
  def __init__(self, cml, id):
    self.__cml = cml
    self.__id = id

  @property
  def cml(self):
    return self.__cml
  
  @property
  def id(self):
    return self.__id
  
  @property
  def name(self):
    return self.data['ui']['label']
  
  @property
  def data(self):
    return yaml.safe_load(self.get())
  
  @property
  def description(self):
    return self.data['general']['description']
  
  @property
  def type(self):
    return self.get
  
  @property
  def path(self):
    return f"node_definitions/{self.id}"
  
  def __build_path(self, path=None):
    full_path = self.path
    if path: full_path += "/" + path
    return full_path
  
  def get(self, path=None, parameters=None):
    return self.cml.get(self.__build_path(path), parameters)


####################
###  Lab object  ###
####################
class Lab(object):
  def __init__(self, cml, id):
    self.__cml = cml
    self.__id = id
  
  def __getattr__(self, attr):
    try:
      node = self.get_node_by_name(attr)
    except:
      raise Exception(f"Object 'Lab' has no attribte '{attr}'.")
    return node
  
  @property
  def path(self):
    return f"labs/{self.id}"

  @property
  def cml(self):
    return self.__cml

  @property
  def id(self):
    return self.__id
  
  @property
  def title(self):
    return self.get()['lab_title']
  
  @property
  def name(self):
    return self.title
  
  @title.setter
  def title(self, title):
    self.patch(data=json.dumps({'title': title}))
  
  @property
  def description(self):
    return self.__cml.get(f"labs/{self.id}")['lab_description']
  
  @description.setter
  def description(self, description):
    self.patch(data=json.dumps({'description': description}))

  @property
  def data(self):
    return self.get()
  
  @property
  def state(self):
    return self.get("state")
  
  @property
  def nodes(self):
    nodes = self.get("nodes")
    return [Node(self, node_id) for node_id in nodes]
  
  @property
  def links(self):
    return [Link(self, link) for link in self.get('links')]
  
  def __build_path(self, path=None):
    full_path = self.path
    if path: full_path += "/" + path
    return full_path

  def get(self, path=None, parameters=None):
    return self.cml.get(self.__build_path(path), parameters)
  
  def post(self, path=None, data=None):
    return self.cml.post(self.__build_path(path), data=data)
  
  def put(self, path=None):
    self.cml.put(self.__build_path(path))
  
  def patch(self, path=None, data=None):
    self.cml.patch(self.__build_path(path), data)
  
  def delete(self, path=None):
    self.cml.delete(self.__build_path(path))
  
  def start(self):
    self.put("start")

  def stop(self):
    self.put("stop")
  
  def wipe(self):
    self.put("wipe")
  
  def create_node(self, name, node_definition, x=0, y=0):
    data = {
      'label': name,
      'node_definition': node_definition,
      'x': x,
      'y': y
    }
    if isinstance(node_definition, Node_Definition):
      data['node_definition'] = node_definition.id
    js = self.post("nodes", data)
    return Node(self, js['id'])
  
  def get_node_by_name(self, name):
    for node in self.nodes:
      if node.name == name:
        return node
    raise Exception(f"A node named {name} was not found in the {self.title} lab.")

  def create_link(self, source, dest):
    if isinstance(source, Node):
      source = source.first_available_interface()
    src_ifc = source.id
    if isinstance(dest, Node):
      dest = dest.first_available_interface()
    dst_ifc = dest.id
    data = {
      "src_int": src_ifc,
      "dst_int": dst_ifc
    }
    js = self.post("links", data)
    return Link(self, js['id'])
    

#####################
###  Node Object  ###
#####################
class Node(object):
  def __init__(self, lab, id):
    self.__lab = lab
    self.__id = id

  def __getattr__(self, attr):
    try:
      node = self.get_interface(attr.replace("_", "/"))
    except:
      raise Exception(f"Object 'Node' has no attribte '{attr}'.")
    return node
  
  @property
  def lab(self):
    return self.__lab
  
  @property
  def id(self):
    return self.__id
  
  @property
  def path(self):
    return "/nodes/" + self.id
  
  @property
  def data(self):
    return self.get()
  
  @property
  def name(self):
    return self.data['label']
  
  @name.setter
  def name(self, name):
    self.patch(data={'label':name})
  
  @property
  def state(self):
    return self.data['state']
  
  @property
  def converged(self):
    return self.get("check_if_converged")
  
  @property
  def x(self):
    return self.data['x']
  
  @x.setter
  def x(self, x):
    self.patch(data={'x':x})
  
  @property
  def y(self):
    return self.data['y']
  
  @y.setter
  def y(self, y):
    self.patch(data={'y':y})
  
  @property
  def configuration(self):
    return self.data['configuration']
  
  @configuration.setter
  def configuration(self, configuration):
    self.patch(data={'configuration':configuration})
  
  @property
  def interfaces(self):
    return [Interface(self, interface) for interface in self.get('interfaces')]
  
  @property
  def node_definition(self):
    return self.lab.cml.get_node_definition_by_name(self.data['node_definition'])

  def __build_path(self, path=None):
    full_path = self.path
    if path: full_path += "/" + path
    return full_path
  
  def get(self, path=None, parameters=None):
    return self.lab.get(self.__build_path(path), parameters)
  
  def post(self, path=None, data=None):
    return self.lab.post(self.__build_path(path), data=data)
  
  def patch(self, path=None, data=None):
    return self.lab.patch(self.__build_path(path), data)
  
  def put(self, path=None):
    self.lab.put(self.__build_path(path))
  
  def delete(self, path=None):
    self.lab.delete(self.__build_path(path))
  
  def start(self):
    self.put("state/start")
  
  def stop(self):
    self.put("state/stop")
  
  def wipe(self):
    self.put("wipe_disks")
  
  def create_interface(self, slot=None):
    data = {'node': self.id}
    if slot: data['slot'] = slot
    js = self.lab.post('interfaces', data=data)
    if not type(js) is list: 
      id = js['id']
    elif slot:
      id = [ifc['id'] for ifc in js if ifc['slot'] == slot][0]
    else:
      id = js[-1]['id']
    return Interface(self, id)
  
  def get_interface(self, search_string):
    if type(search_string) is int or search_string.isdigit():
      matches = [ifc for ifc in self.interfaces if ifc.slot == int(search_string)]
    else:
      matches = [ifc for ifc in self.interfaces if ifc.name_match(search_string)]
    if not matches:
      raise Exception(f"Interface {search_string} not found.")
    return matches[0]
  
  def first_available_interface(self):
    for ifc in self.interfaces:
      if ifc.type == "physical" and not ifc.connected:
        return ifc
    return None


#########################
###  Interface Object ###
#########################
class Interface(object):
  def __init__(self, node, id):
    self.__node = node
    self.__id = id

  @property
  def node(self):
    return self.__node
  
  @property
  def lab(self):
    return self.node.lab
  
  @property
  def id(self):
    return self.__id
  
  @property
  def data(self):
    return self.get()
  
  @property
  def label(self):
    return self.data['label']
  
  @property
  def name(self):
    return self.label
  
  @property
  def type(self):
    return self.data['type']
  
  @property
  def slot(self):
    return self.data['slot']
  
  @property
  def mac_address(self):
    return self.data['mac_address']
  
  @property
  def connected(self):
    return self.data['is_connected']
  
  @property
  def state(self):
    return self.data['state']
    
  @property
  def path(self):
    return f"/interfaces/{self.id}"
  
  @property
  def link(self):
    for link in self.lab.links:
      if self.id in [link.source_interface.id, link.dest_interface.id]:
        return link
    return None
  
  def __build_path(self, path=None):
    full_path = self.path
    if path: full_path += "/" + path
    return full_path
  
  def get(self, path=None, parameters=None):
    return self.lab.get(self.__build_path(path), parameters)
  
  def put(self, path=None):
    self.lab.put(self.__build_path(path))
  
  def delete(self):
    self.lab.delete(self.path)
  
  def start(self):
    self.put('state/start')
  
  def stop(self):
    self.put('state/stop')
  
  def create_link(self, destination):
    return self.lab.create_link(self, destination)\
  
  def name_match(self, name):
    if name == self.name: 
      return True
    ifc_split = interface_name_split(self.name)
    name_split = interface_name_split(name)
    if ifc_split[0].lower()[:len(name_split[0])] == name_split[0].lower() and ifc_split[1] == name_split[1]:
      return True
    return False
    

#####################
###  Link Object  ###
#####################
class Link(object):
  def __init__(self, lab, id):
    self.__lab = lab
    self.__id = id
  
  @property
  def lab(self):
    return self.__lab
  
  @property
  def id(self):
    return self.__id
  
  @property
  def path(self):
    return f"links/{self.id}"
  
  @property
  def data(self):
    return self.get()
  
  @property
  def source_node(self):
    return Node(self.lab, self.data['node_a'])
  
  @property
  def source_interface(self):
    return Interface(self.source_node, self.data['interface_a'])
  
  @property
  def dest_node(self):
    return Node(self.lab, self.data['node_b'])
  
  @property
  def dest_interface(self):
    return Interface(self.dest_node, self.data['interface_b'])
  
  @property 
  def state(self):
    return self.data['state']

  @property 
  def label(self):
    return self.data['label']
  
  @property
  def capture(self):
    return Capture(self)
  
  def __build_path(self, path=None):
    full_path = self.path
    if path: full_path += "/" + path
    return full_path

  def get(self, path=None, parameters=None):
    return self.lab.get(self.__build_path(path), parameters)
  
  def put(self, path=None):
    self.lab.put(self.__build_path(path))
  
  def delete(self):
    self.lab.delete(self.__build_path())
  
  def start(self):
    self.put("state/start")
  
  def stop(self):
    self.put("state/stop")
  

########################
###  Capture Object  ###
########################
class Capture(object):
  def __init__(self, link):
    self.__link = link
  
  @property
  def link(self):
    return self.__link
  
  @property
  def path(self):
    return "capture"
  
  @property
  def status(self):
    return self.get("status")
  
  @property
  def key(self):
    return self.get("key")
  
  def __build_path(self, path=None):
    full_path = self.path
    if path: full_path += f"/{path}"
    return full_path
  
  def get(self, path=None, parameters=None):
    return self.link.get(self.__build_path(path))
  
  def put(self, path=None):
    self.link.put(self.__build_path(path))
  
  def start(self):
    self.put("start")
  
  def stop(self):
    self.put("stop")
