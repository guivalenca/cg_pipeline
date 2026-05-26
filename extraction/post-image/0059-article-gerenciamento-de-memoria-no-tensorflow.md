---
id: "59"
title: "Gerenciamento de Memória no Tensorflow"
source_url: "https://medium.com/ibm-data-ai/memory-hygiene-with-tensorflow-during-model-training-and-deployment-for-inference-45cf49a15688"
fetch_url: "https://medium.com/ibm-data-ai/memory-hygiene-with-tensorflow-during-model-training-and-deployment-for-inference-45cf49a15688"
resolved_url: "https://medium.com/ibm-data-ai/memory-hygiene-with-tensorflow-during-model-training-and-deployment-for-inference-45cf49a15688"
firecrawl_title: "Memory Hygiene With TensorFlow During Model Training and Deployment for Inference | by Tanveer Khan | IBM Data Science in Practice | Medium"
description: "Memory Hygiene With TensorFlow During Model Training and Deployment for Inference Introduction If you work on TensorFlow and want to share GPU with multiple processes then you must have encountered …"
fetched_at: "2026-05-12T03:59:52.430958Z"
provider: "firecrawl"
strategy: "static_with_actions"
cache_key: "bc954294499ac3eafb94048d7b0cf25f4de528118ff585fdc41e499e3ab8d78b"
firecrawl_status_code: 200
firecrawl_content_type: "text/html; charset=utf-8"
word_count: 2356
char_count: 14501
content_sha256: "158a0bcff4f3c7dcf8ed567400ae74f27cc1556e184448bfa193d0cd68d3d2ad"
image_count: 169
link_count: 108
warnings: []
gate_status: "passed"
gate_failures: []
route_notes:
  - "medium_can_return_deleted_or_member_wall"
---

# Memory Hygiene With TensorFlow During Model Training and Deployment for Inference

[Image: Tanveer Khan](https://miro.medium.com/v2/resize:fill:32:32/0*f7_9heADDvAKBkON.)

[Tanveer Khan](https://medium.com/@khantanveerak?source=post_page---byline--45cf49a15688---------------------------------------)

Follow

7 min read
·
Mar 9, 2021

## Introduction

If you work on TensorFlow and want to share GPU with multiple processes then you must have encountered into either of one of the below situations. This post discusses how to address these situations and use the GPU resources optimally to take maximum advantage of it.

Press enter or click to view image in full size

Image summary: The image shows two situations. In situation 1, one person says a model is training on the GPU and the entire memory is occupied, so another training job must wait. In situation 2, one person says they have only one GPU and need to deploy multiple models for inference at the same time. [Original image: Image with stick figures. In situation one, the stick figure on the left says “hey- are you training some model on GPU. Seems entire memory is occupied. I need to train my model.” The stick figure on the right replies “oh yes, you would need to wait for a few hours.” In situation two, the stick figure says “I have only one GPU and need to deploy couple of models for inference simultaneously”](https://miro.medium.com/v2/resize:fit:700/1*KHptmSM4R9TXHuOA6EXMtQ.png)

**Technical Details:**

- GPU — Nvidia RTX 3080  
- CPU & Memory — Intel i7, 32 GB RAM  
- TensorFlow Version — 2.4  
- CUDA Version — 11.2  
- Application — TensorFlow application that I will be discussing is Automated Number Plate Recognition which is built on Darknet as backbone network

Let’s see Memory Allocation For a TensorFlow-Based Model on a GPU:

These are the GPU memory details before loading any TensorFlow Based Workload.

It can be clearly observed that GPU has 10 GB of memory and of which only 489 MB is occupied.

Press enter or click to view image in full size

Image summary: This nvidia-smi output shows an RTX 3080 with 10,009 MiB of GPU memory, of which 489 MiB is already in use before any TensorFlow workload runs. The table also lists current GPU processes and their memory usage. [Original image: This image is an output of command nvidia-smi which is used to print stats about Nvidia GPU. This image shows 490 MB of memory is allocated to the GPU before running any Tensorflow based workload.](https://miro.medium.com/v2/resize:fit:700/1*JjnEw4gA_OQoiHySh21l_A.png)

Initial GPU Memory Allocation Before Executing Any TF Based Process

Now let’s load a TensorFlow-based process.

We will load an object detection model deployed as REST-API via Flask \[1\] running over Twisted \[2\].

You can see how quickly the complete GPU memory is filled up as soon as TensorFlow model is loaded:

Screen Grab For TF Memory Allocation - YouTube

Tap to unmute

1x

[Screen Grab For TF Memory Allocation](https://www.youtube.com/watch?v=MYwBRnRAKW0) [Tanveerkhan867](https://www.youtube.com/channel/UC3OyAeQCIxSxwIT7NvrlArQ)

[Image: thumbnail-image](https://yt3.ggpht.com/WVjkhmadYzNKX5IbPIQVhxgDK3qu2wUet0RxXRaGPaibN-24t9z6z1wGN0dwwtjxJbRhV_F9phc=s68-c-k-c0x00ffffff-no-rj)

Tanveerkhan86710 subscribers

[Watch on](https://www.youtube.com/watch?v=MYwBRnRAKW0)

\`Full Memory Allocation

So if we try to start another process it will give you an Out of Memory Error.

Our inference module is exposed as a REST API which listens for inference requests on a specified Port. Since we are already running a process, that Port is in use. If we run one more instance of the process, it will fail as that port is in use. To avoid this error, we will just change the Port Number where our REST service will listen and run the same process.

Screen grab for Out Of Memory Error - YouTube

Tap to unmute

1x

[Screen grab for Out Of Memory Error](https://www.youtube.com/watch?v=LKzuZOOhcsM) [Tanveerkhan867](https://www.youtube.com/channel/UC3OyAeQCIxSxwIT7NvrlArQ)

[Image: thumbnail-image](https://yt3.ggpht.com/WVjkhmadYzNKX5IbPIQVhxgDK3qu2wUet0RxXRaGPaibN-24t9z6z1wGN0dwwtjxJbRhV_F9phc=s68-c-k-c0x00ffffff-no-rj)

Tanveerkhan86710 subscribers

[Watch on](https://www.youtube.com/watch?v=LKzuZOOhcsM)

Out of memory error

_The above video clearly shows the out of memory error. TensorFlow aggressively occupies the full GPU memory even though it actually doesn’t need to do so._

_This is a greedy strategy adopted by TensorFlow to avoid memory fragmentation, but this causes a bottleneck of GPU memory. Only one process exclusively has all the memory._

[**Use a GPU \| TensorFlow Core** 
\ 
**TensorFlow code, and models will transparently run on a single GPU with no code changes required. Use Note…**\ 
\
www.tensorflow.org](https://www.tensorflow.org/guide/gpu?source=post_page-----45cf49a15688---------------------------------------)

By default, TensorFlow maps nearly all of the GPU memory of all GPUs (subject to `CUDA_VISIBLE_DEVICES`) visible to the process. This is done to more efficiently use the relatively precious GPU memory resources on the devices by reducing memory fragmentation. To limit TensorFlow to a specific set of GPUs we use the `tf.config.experimental.set_visible_devices` method.

Due to the default setting of TensorFlow, even if a model can be executed on far less memory, many times a model will occupy far more memory than needed. This results in non-optimal and often wastage of computation power of a GPU.

If the optimal memory is allocated to a TensorFlow process, it will occupy less GPU memory and the remaining memory can be shared by other process.

So either you can train multiple models at one go or you can execute multiple model for inference at the same time.

## TensorFlow has provided Two options to address this situation:

### **First Option — Specifically Set The Memory**

We need to add the line below to list the GPU(s) you have.

```
 gpus = tf.config.list_physical_devices('GPU')
```

In this option, we can limit or restrict TensorFlow to use only specified memory from the GPU. In this way, you can limit memory and have a fair share on the GPU between the different processes. Using this option you can define the optimal memory for your process and it will use only that memory.

Setting this optimal memory can be tricky. You can use tools like Weight and Biases \[3\] and Tensorboard \[4\] to look at the System Graphs to come-up with an optimal memory size for your process. These tools generate very useful graphs with details about your GPU computation, utilization, memory usage and memory transfer.

## Get Tanveer Khan’s stories in your inbox

Join Medium for free to get updates from this writer.

Subscribe

Remember me for faster sign in

We will add below code to our process and will execute

```
if gpus:
    for gpu in gpus:
        tf.config.experimental.set_virtual_device_configuration(gpu,[tf.config.experimental.VirtualDeviceConfiguration(memory_limit=4096)])
```

In the above code, we are setting an upper bound of 4 GB on GPU memory limit. So when we trigger the process, it will occupy only 4 GB of memory instead of occupying the full memory.

Let’s look at the screenshot of nvidia-smi command to know the memory usage of GPU after executing our process which is bounded to use only 4 GB of memory. It can be observed that only 4 GB of memory is used instead of 8 GB as shown in the first video.

Press enter or click to view image in full size

Image summary: The nvidia-smi output shows a GeForce RTX 3080 with 10,009 MiB total GPU memory and about 4,700 MiB in use after starting one TensorFlow process. This illustrates that the process is constrained to roughly 4 GB of GPU memory instead of taking the full device memory. [Original image: This image shows GPU memory allocated via nvidia-smi command. This is a standard command to display GPU stats including utilization, memory usage and temperature of Nvidia GPU. This image shows memory usage has increased by 4GB as we had allocated 4GB memory to our process.](https://miro.medium.com/v2/resize:fit:700/1*HCrvlyixgdiKgvIZXzdafQ.png)

GPU Memory Allocated After Starting One Process with 4 GB Memory Allocation

Now let’s execute the other process which has previously faced Out Of Memory Error.

Press enter or click to view image in full size

Image summary: The screenshot shows two TensorFlow-based inference processes running at the same time while nvidia-smi reports GPU memory split between them. The left and right panels show process logs, and the middle panel shows GPU memory usage increasing to about 8 GB total, indicating each process is using its allocated share rather than taking all GPU memory. [Original image: This image has three screen shots. Left and right panel of the image is a log from a inference from Tensorflow based process that is exposed as REST using Flask and ran via Twisted. The middle panel of the image shows GPU memory allocated via nvidia-smi command. This image shows memory usage has increased by 8 GB we had allocated 4GB memory to each process. This image shows both the process are able to ran using their equal share of GPU memory.](https://miro.medium.com/v2/resize:fit:700/1*VCDtaDyPu47jvyMS1jSdxA.png)

Two process running simultaneously with-in their allocated memory

Attached is the screen grab for whole process:

Memory Management Tensorflow - YouTube

Tap to unmute

1x

[Memory Management Tensorflow](https://www.youtube.com/watch?v=D7MZT7Wwu5Y) [sheepcraft7555](https://www.youtube.com/channel/UCaFbhH7fZTr6I8TewsEUpFw)

[Image: thumbnail-image](https://yt3.ggpht.com/V1c98tc6FvZceRVLQT9nzQzg1cX2tFXjjV8pjke6gA9t0knryPN0ky3Cd4xdNLeysuYUx1jSLw=s68-c-k-c0x00ffffff-no-rj)

sheepcraft7555512 subscribers

[Watch on](https://www.youtube.com/watch?v=D7MZT7Wwu5Y)

We have clearly seen that using this option, we can allocate/override GPU memory allocation for the TensorFlow process and can use GPU resources optimally between the team or process.

### **Second option** — Set memory growth as per the need

This option will initially allocate just a little memory and will keep on allocating more. _However, there is one caveat with this option. Once the memory is allocated, it will not be released to avoid memory fragmentation. So even if your process starts on low memory, it will acquire more memory gradually but it will not release when it don’t need it. I would recommend to use the first option whenever possible._

The code snippet below sets the second option discussed in the blog post which will initially allocate the minimum required memory and later on increase the memory allocation as needed for the TensorFlow-based workflow. The first line finds out if and how many GPU’s are available and for each GPU, it says to use the set_memory_growth_option

```
 gpus = tf.config.list_physical_devices('GPU')
 if gpus:
    for gpu in gpus:
       tf.config.experimental.set_memory_growth(gpu,True)
```

Let’s execute my process one more time and see the memory allocation.

Press enter or click to view image in full size

Image summary: A terminal screenshot of `nvidia-smi` shows the GPU before the TensorFlow workload starts. The RTX 3080 has 10,009 MiB total memory, and only 352 MiB is in use at this point. [Original image: This image is an output of command nvidia-smi which is used to print stats about Nvidia GPU. This image shows 352 MB of memory is allocated to the GPU before running any Tensorflow based workload.](https://miro.medium.com/v2/resize:fit:700/1*Y6bk_3mWx_aKEelRPs8aiA.png)

GPU Memory Allocation Before Executing A Process With Set Process

**The process is executed. We can see, the full memory is NOT allocated: only few MB’s are allocated.**

Press enter or click to view image in full size

Image summary: The screenshot shows a TensorFlow process running in a terminal on the left and nvidia-smi output on the right. It demonstrates that, with memory growth enabled, the GPU does not reserve all memory up front; only a small amount is allocated initially while the process is active. [Original image: Left Panel of the image shows the log of Tensorflow based process that was executed. It shows process is up and running. Right Panel of the image is an output of command nvidia-smi which is used to print stats about Nvidia GPU. This image shows few MB memory is allocated to the GPU after running Tensorflow based workload. Image shows using this option Tensorflow is taking only what is required.](https://miro.medium.com/v2/resize:fit:700/1*V2PhJh0AutF7_XLA4Iru7Q.png)

Memory Allocated After Executing Process

Now, we will put some load on the GPU. To add more load, we will make 100 REST calls simultaneously to do the object detection which will do the Automatic Number Plate Recognition. This request will go to the REST server and will put load on the GPU and that will cause an increase in GPU memory.

memory growth with increasing load - YouTube

Tap to unmute

1x

[memory growth with increasing load](https://www.youtube.com/watch?v=mkZlinnBdyA) [sheepcraft7555](https://www.youtube.com/channel/UCaFbhH7fZTr6I8TewsEUpFw)

[Image: thumbnail-image](https://yt3.ggpht.com/V1c98tc6FvZceRVLQT9nzQzg1cX2tFXjjV8pjke6gA9t0knryPN0ky3Cd4xdNLeysuYUx1jSLw=s68-c-k-c0x00ffffff-no-rj)

sheepcraft7555512 subscribers

[Watch on](https://www.youtube.com/watch?v=mkZlinnBdyA)

In the above screen grab, we can see the memory gradually increases but it doesn’t occupy the full memory. However, it doesn’t release the memory even after the load on the GPU is gone. (The REST service is still running but inference load is complete).

Press enter or click to view image in full size

Image summary: A terminal `nvidia-smi` screenshot shows the GPU still using about 8 GB of memory after the workload has finished. The key point is that TensorFlow may retain allocated GPU memory instead of releasing it immediately, even when the load is gone. [Original image: This image is an output of command nvidia-smi which is used to print stats about Nvidia GPU. This image shows 8GB memory is allocated to the GPU before running any Tensorflow based workload. This image shows memory usage has increased significantly based upon load but it has not still occupied full memory.](https://miro.medium.com/v2/resize:fit:700/1*l-CX_d1PJ8yQaHlOFpV6Xg.png)

Memory Is Occupied Even Load On GPU Is Finished

## Conclusion:-

1. TensorFlow processes by default will acquire the full memory of the GPU, even if it does not need it. If you build a small neural network, it will acquire the complete GPU memory. This might lead to inefficient GPU utilization if your work load is not heavy.  
2. There are two settings which you can use to control memory acquired by a TensorFlow process.  
3. Specify the exact memory you want to allocate to your process. This will need tuning and experimentation to arrive at the correct number. One can refer to the System Graphs of a GPU. These graphs are available with Weight & Biases. Below are the sample graphs which can be used to evaluate how much memory your process would need to execute.

Press enter or click to view image in full size

Image summary: The figure shows four Weight & Biases process graphs over time: GPU temperature (°C), GPU time spent accessing memory (%), GPU memory allocated (%), and GPU power usage (%). The plots illustrate that memory allocation rises quickly and then stabilizes while the other GPU metrics also increase during the process. [Original image: Graphs showing Process GPU temperature in Celsius, Process GPU Time Spent Accessing Memory by percent, Process GPU Memory Allocated by percent and Process GPU Power Usage by percent](https://miro.medium.com/v2/resize:fit:700/1*xXw9kA3PV3jZTeUZNwnNIQ.png)

Weight & Biases Graph For Process GPU Utilization and Memory Allocation

Press enter or click to view image in full size

Image summary: The dashboard shows four time-series graphs: GPU Utilization (%), GPU Temp (°C), GPU Time Spent Accessing Memory (%), and GPU Memory Allocated (%). The plots indicate GPU utilization and temperature rise quickly and then stabilize, while memory allocated stays high rather than dropping back to zero after the workload finishes. [Original image: Graphs showing GPU utilization by percent, GPU temp in Celsius, GPU time spent accessing memory by percent, and GPU memory allocated by percent](https://miro.medium.com/v2/resize:fit:700/1*fmtxb1HCA4Co4Qc4501Rwg.png)

Weight & Biases Graph For Overall GPU Utilization and Memory Allocation

4\. You can specify a memory growth option. This option will allocate small memory to the process. And it will increase the allocation as needed with increase in load. But it will not release the acquired memory even when the load is complete.

I hope you’ve found this post informative and this helps alleviate any headaches with GPU usage in your next TensorFlow project.

## References

\[1\] [https://flask.palletsprojects.com/en/1.1.x/](https://flask.palletsprojects.com/en/1.1.x/)

\[2\] [https://twistedmatrix.com/trac/](https://twistedmatrix.com/trac/)

\[3\] [https://wandb.ai/site](https://wandb.ai/site)

\[4\] [https://www.tensorflow.org/tensorboard](https://www.tensorflow.org/tensorboard)
