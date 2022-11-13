# Maya Python Metadata Utils

A simple solution for storing python objects as data on a node in Maya.

Lots of metadata solutions involve wrapping the complex nature of Maya's node attribute types and quirks to allow easy
storing and retrieving of data, and connecting nodes via message attributes. PyMetaNode aims to avoid (most of) maya's
attributes altogether for simplicity and flexibility. This places the responsibility of controlling data structures
completely on the tools, and treats the nodes purely as storage.

There are several advantages of using Maya nodes for storing data vs. alternate methods, such as not requiring any other
files other than the maya scene containing the node, and the ability to undo and redo changes in nodes, and therefore
changes in data.

## Design Goals

- Simple
  - A very concise and straightforward api.
  - No need for custom plugin nodes to store your custom data.
- Fast
  - Uses Maya api for all critical operations.

## Features

- Store basic python object types (any type supported by pythons `eval`).
- Store references to other nodes inside metadata.
- Store data for multiple meta classes on a single node.
- Find any node with metadata.
- Find nodes with metadata for a specific metaclass.

## Installation

- Download the [latest release](https://github.com/bohdon/maya-pymetanode/releases/latest)
- Unzip and copy the contents to:
  - Windows: `~/Documents/maya/modules/`
  - Mac: `~/Library/Preferences/Autodesk/maya/modules/`
  - Linux: `~/maya/modules/`

> Note that you may need to create the `modules` folder if it does not exist.

Once installed, the result should look like this:

```
.../modules/pymetanode/
.../modules/pymetanode.mod
```

## Basic Usage

```python
import pymel.core as pm
import pymetanode as meta

# create some example data
my_data = {"myList": [1, 2, 3], "myTitle": "ABC"}
# data must be associated with a metaclass
my_meta_class = "MyMetaClass"
# set meta data on the selected node
node = pm.selected()[0]
meta.set_metadata(node, my_meta_class, my_data)

# retrieve the stored data for 'MyMetaClass' only
# result: {"myList":[1,2,3], "myTitle":"ABC"}
meta.get_metadata(node, my_meta_class)

# retrieve all metadata on the node
# result: {"MyMetaClass": {"myList":[1,2,3], "myTitle":"ABC"}}
meta.get_metadata(node)

# check if a node has meta data for a meta class
# result: True
meta.has_metaclass(node, "MyMetaClass")

# check if a node has any meta data
# result: True
meta.is_meta_node(node)

# find all nodes in the scene that have metadata for a class
meta.find_meta_nodes("MyMetaClass")
```

## How does it work

The implementation is very simple: python data is serialized into a string that is stored on a Maya node, and
deserialized using `ast.literal_eval` when retrieved. Each 'metaclass' type adds an attribute on the node that is used
to perform fast searching for nodes by metaclass. Data goes through a basic encoding and decoding that allows node
references and other potential future features.

## Running Tests

- Add mayapy directory to `PATH` environment variable.
- From the root directory of this repository, run `setup.sh test`
