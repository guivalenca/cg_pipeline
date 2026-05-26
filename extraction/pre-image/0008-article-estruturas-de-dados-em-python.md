---
id: "8"
title: "Estruturas de Dados em Python"
source_url: "https://www.geeksforgeeks.org/python-data-structures/"
fetch_url: "https://www.geeksforgeeks.org/python-data-structures"
resolved_url: "https://www.geeksforgeeks.org/dsa/python-data-structures-and-algorithms/"
firecrawl_title: "DSA with Python - Data Structures and Algorithms - GeeksforGeeks"
description: "Your All-in-One Learning Portal: GeeksforGeeks is a comprehensive educational platform that empowers learners across domains-spanning computer science and programming, school education, upskilling, commerce, software tools, competitive exams, and more., Your All-in-One Learning Portal. It contains well written, well thought and well explained computer science and programming articles, quizzes and practice/competitive programming/company interview Questions."
fetched_at: "2026-05-12T03:59:51.135342Z"
provider: "firecrawl"
strategy: "app_ui"
cache_key: "07acdb8e99a673ebd27b4a7134564a09cc165d7cc5a741edd5ab520b0b287f32"
firecrawl_status_code: 200
firecrawl_content_type: "text/html; charset=utf-8"
word_count: 1386
char_count: 9056
content_sha256: "028034e05c4e206de2fca010689fb3847860a34eee921ad9bc9d5fc7a71fa3d8"
image_count: 5
link_count: 135
warnings: []
gate_status: "passed"
gate_failures: []
route_notes:
  - "template_heavy_preserve_code_blocks"
---

# DSA with Python - Data Structures and Algorithms

Last Updated : 10 Oct, 2025

This tutorial is a beginner-friendly guide for learning data structures and algorithms using Python. In this article, we will discuss the in-built data structures such as lists, tuples, dictionaries, etc. and some user-defined data structures such as linked lists, trees, graphs, etc.

### 1. List

List is a built-in dynamic array which can store elements of different data types. It is an ordered collection of item, that is elements are stored in the same order as they were inserted into the list. List stores references to the objects (elements) rather than storing the actual data itself.

```python
# Loading Playground...

# Python
a = [10, 20, "GfG", 40, True]
print(a)
```

**Output**
```python
[10, 20, 'GfG', 40, True]
```

![python-list](https://media.geeksforgeeks.org/wp-content/uploads/20250117155408431412/python-list.webp)

### 2. Searching Algorithms

Searching algorithms are used to locate a specific element within a data structure, such as an array, list, or tree. They are used for efficiently retrieving information in large datasets.

```python
# Loading Playground...

# Python
import bisect
a = [2, 4, 6, 8, 10]

# Linear search using 'in'
print(6 in a)

# Linear search using 'count'
print(a.count(7) > 0)

# Binary search using bisect
pos = bisect.bisect_left(a, 8)
print("Found at index:", pos)
```

**Output**
```python
True
False
Found at index: 3
```

### 3. Sorting Algorithms

Sorting algorithms are used to arrange the elements of a data structure, such as an array, list, or tree, in a particular order, typically in ascending or descending order. These algorithms are used for organizing data, which enables more efficient searching, merging, and other operations.

```python
# Loading Playground...

# Python
nums = [5, 3, 8, 1]

# In-place sort
nums.sort()
print(nums)

# New sorted list (descending)
print(sorted(nums, reverse=True))
```

**Output**
```python
[1, 3, 5, 8]
[8, 5, 3, 1]
```

### 4. String

String is a sequence of characters enclosed within single quotes (' ') or double quotes (" "). They are **immutable**, so once a string is created, it cannot be altered. Strings can contain letters, numbers, and special characters, and they support a wide range of operations such as slicing, concatenation, etc.

```python
# Loading Playground...

# Python
s = "Hello Geeks"
print(s)
```

**Output**
```python
Hello Geeks
```

### 5. Set

Set is a built-in collection in Python that can store unique elements of different data types. It is an unordered collection, meaning the elements do not maintain any specific order as they are added. Sets do not allow duplicate elements and automatically remove duplicates.

```python
# Loading Playground...

# Python
a = {10, 20, 20, "GfG", "GfG", True, True}
print(a)
```

**Output**
```python
{'GfG', 10, 20, True}
```

### 6. Dictionary

Dictionary is a mutable, unordered (after Python 3.7, dictionaries are ordered) collection of data that stores data in the form of key-value pair. It is like hash tables in any other language. Each key in a dictionary is unique and immutable, and the values associated with the keys can be of any data type, such as numbers, strings, lists, or even other dictionaries. We can create a dictionary by using curly braces ({}).

```python
# Loading Playground...

# Python
# Creating a Dictionary
d = {10 : "hello", 20 : "geek", "hello" : "world", 2.0 : 55}
print(d)
```

**Output**
```python
{10: 'hello', 20: 'geek', 'hello': 'world', 2.0: 55}
```

### 7. Recursion

Recursion is a programming technique where a function calls itself in order to solve smaller instances of the same problem. It is usually used to solve problems that can be broken down into smaller instances of the same problem.

```python
# Loading Playground...

# Python
def fact(n):
    if n == 0:
        return 1
    return n * fact(n - 1)

print(fact(5))
```

**Output**
```python
120
```

### 8. Stack

Stack is a linear data structure that stores items in a Last-In/First-Out (LIFO) manner. In stack, a new element is added at one end and an element is removed from that end only. The insert and delete operations are often called push and pop.

```python
# Loading Playground...

# Python
stack = []

# append() function to push element in the stack
stack.append('g')
stack.append('f')
stack.append('g')

print('Initial stack')
print(stack)

# pop() function to pop element from stack in LIFO order
print('\nElements popped from stack:')
print(stack.pop())
print(stack.pop())
print(stack.pop())

print('\nStack after elements are popped:')
print(stack)
```

**Output**
```python
Initial stack
['g', 'f', 'g']

Elements popped from stack:
g
f
g

Stack after elements are popped:
[]
```

### 9. Queue

Queue is a data structure that follows the First-In, First-Out (FIFO) principle, meaning the first element added is the first one to be removed. The insert and delete operations are often called enqueue and dequeue.

```python
# Loading Playground...

# Python
queue = []

# Adding elements to the queue
queue.append('g')
queue.append('f')
queue.append('g')

print("Initial queue")
print(queue)

# Removing elements from the queue
print("Elements dequeued from queue")
print(queue.pop(0))
print(queue.pop(0))
print(queue.pop(0))

print("Queue after removing elements")
print(queue)
```

**Output**
```python
Initial queue
['g', 'f', 'g']
Elements dequeued from queue
g
f
g
Queue after removing elements
[]
```

### 10. Linked List

Linked List is a linear data structure where elements, called nodes, are stored in a sequence. Each node contains two parts: the data and a reference (or link) to the next node in the sequence.

```python
# Loading Playground...

# Python
# Node class
class Node:
    def __init__(self, data):
        self.data = data
        self.next = None

if __name__=='__main__':

    # Create a linked list
    # 10 -> 20 -> 30
    head = Node(10)
    head.next = Node(20)
    head.next.next = Node(30)

    # Print the list
    temp = head
    while temp != None:
        print(temp.data, end = " ")
        temp = temp.next
```

**Output**
```python
10 20 30
```

### 11. Tree

Tree Data Structure is a non-linear data structure in which a collection of elements known as nodes are connected to each other via edges such that there exists exactly one path between any two nodes.

```python
# Loading Playground...

# Python
# Structure of a Binary Tree Node
class Node:
    def __init__(self, v):
        self.data = v
        self.left = None
        self.right = None

def printInorder(root):
    if(root == None):
        return
    printInorder(root.left)
    print(root.data, end = " ")
    printInorder(root.right)

if __name__ == '__main__':

    # Construct Binary Tree of 4 nodes
    root = Node(1)
    root.left = Node(2)
    root.right = Node(3)
    root.left.left = Node(4)

    printInorder(root)
```

**Output**
```python
4 2 1 3
```

### 12. Heap

Heap is a complete binary tree that satisfies the heap property. It can be used to implement a priority queue.

```python
# Loading Playground...

# Python
import heapq
a = [5, 7, 9, 1, 3]

# using heapify to convert list into heap
heapq.heapify(a)

# printing created heap
print ("The created heap is:", a)

# Push 4 into the heap
heapq.heappush(a, 4)

# printing modified heap
print ("The modified heap after push is:", a)

# using heappop() to pop smallest element
print ("The smallest element is:", heapq.heappop(a))
```

**Output**
```python
The created heap is: [1, 3, 9, 7, 5]
The modified heap after push is: [1, 3, 4, 7, 5, 9]
The smallest element is: 1
```

### 13. Graphs

Graph is a non-linear data structure consisting of a collection of nodes (or vertices) and edges (or connection between the nodes).

```python
# Loading Playground...

# Python
# Function to add an edge between two vertices
def addEdge(adj, u, v, w):
    adj[u].append((v, w))
    adj[v].append((u, w))

def displayAdjList(adj):
    for i in range(len(adj)):
        print(f"{i}: ", end="")
        for j in adj[i]:
            print(f"{{{j[0]}, {j[1]}}} ", end="")
        print()

def main():

    # Create a graph with 3 vertices and 3 edges
    V = 3
    adj = [[] for _ in range(V)]

    # Now add edges one by one
    addEdge(adj, 1, 0, 4)
    addEdge(adj, 1, 2, 3)
    addEdge(adj, 2, 0, 1)

    print("Adjacency List Representation:")
    displayAdjList(adj)

if __name__ == "__main__":
    main()
```

**Output**
```python
Adjacency List Representation:
0: {1, 4} {2, 1}
1: {0, 4} {2, 3}
2: {1, 3} {0, 1}
```

### 14. Dynamic Programming

Dynamic Programming (DP) is a technique for solving problems by breaking them into smaller subproblems and storing their solutions to avoid redundant computations. 

![Dynamic-Programming-or-DP-1.webp](https://media.geeksforgeeks.org/wp-content/uploads/20250106170245473186/Dynamic-Programming-or-DP-1.webp)![Dynamic-Programming-or-DP-2.webp](https://media.geeksforgeeks.org/wp-content/uploads/20250106170245668624/Dynamic-Programming-or-DP-2.webp)
