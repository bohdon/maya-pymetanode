# Maya Python Meta Node

A simple solution for storing python objects as data on a node in Maya.

Lots of meta data solutions involve wrapping the complex nature of Maya's node attribute types and quirks to allow easy storing and retrieving of data, and connecting nodes via message attributes. PyMetaNode aims to avoid (most of) maya's attributes altogether for simplicity and flexibility. This places the responsibility of controlling data structures completely on the tools, and treats the nodes purely as storage.

There are several advantages of using Maya nodes for storing data vs. alternate methods, such as not requiring any other files other than the maya scene containing the node, and the ability to undo and redo changes in nodes, and therefore changes in data.


## Design Goals

- Simple
  - a very concise and straightforward api
  - no need for custom plugin nodes to store your custom data
- Fast
  - uses Maya api for all critical operations


## Features

- Store data for multiple meta classes on a single node
- Store basic python object types (any type supported by pythons `eval`)
- Store references to other nodes inside meta data (planned)
- Find any node with meta data
- Find nodes with meta data for a specific meta class

## Basic Usage

```python
import pymel.core as pm
import pymetanode as meta

# create some example data
myData = {'myList':[1,2,3], 'myTitle':'ABC'}
# data must be associated with a meta class
myMetaClass = 'MyMetaClass'
# set meta data on the selected node
node = pm.selected()[0]
meta.setMetaData(node, myMetaClass, myData)


# retrieve the stored data for 'MyMetaClass' only
# result: {'myList':[1,2,3], 'myTitle':'ABC'}
meta.getMetaData(node, myMetaClass)

# retrieve all meta data on the node
# result: {'MyMetaClass': {'myList':[1,2,3], 'myTitle':'ABC'}}
meta.getMetaData(node)

# check if a node has meta data for a meta class
# result: True
meta.hasMetaClass(node, 'MyMetaClass')

# check if a node has any meta data
# result: True
meta.isMetaNode(node)

# find all nodes in the scene that have meta data for a class
meta.findMetaNodes('MyMetaClass')
```


## How does it work

The implementation is very simple: python data is serialized into a string that is stored on a Maya node, and deserialized using `eval` when retrieved. Each 'meta class' type adds an additional attribute on the node that is used to perform fast searching for nodes. Data goes through a basic encoding and decoding that allows node references and other potential future features.


## Version 1.0.0 (2017-12-19)
- Initial release
