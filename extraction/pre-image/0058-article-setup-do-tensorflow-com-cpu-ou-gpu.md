---
id: "58"
title: "Setup do Tensorflow com CPU ou GPU"
source_url: "https://www.tensorflow.org/install/pip?hl=pt-br"
fetch_url: "https://www.tensorflow.org/install/pip?hl=pt-br"
resolved_url: "https://www.tensorflow.org/install/pip?hl=pt-br"
firecrawl_title: "Instale o TensorFlow com pip"
description: null
fetched_at: "2026-05-12T03:59:52.307691Z"
provider: "firecrawl"
strategy: "standard"
cache_key: "8df7657c8dc46f61374f1b53dabeb27fd395ffa5eb2286d0e61455e9a3446b21"
firecrawl_status_code: 200
firecrawl_content_type: "text/html; charset=utf-8"
word_count: 2147
char_count: 14016
content_sha256: "6daf912936b50d5e15514a679999f8d8069ecf8f0ed3e2bf4b7981f21623c4b4"
image_count: 2
link_count: 72
warnings: []
gate_status: "passed"
gate_failures: []
route_notes: []
---

# Instale o TensorFlow com pip

Este guia é para a versão estável mais recente do TensorFlow. Para a versão prévia _(nightly)_ , use o pacote pip chamado `tf-nightly` . Consulte [estas tabelas](https://www.tensorflow.org/install/source?hl=pt-br#tested_build_configurations) para ver os requisitos de versões mais antigas do TensorFlow. Para a compilação somente CPU, use o pacote pip denominado `tensorflow-cpu` .

Aqui estão as versões rápidas dos comandos de instalação. Role para baixo para obter instruções passo a passo.

```bash
python3 -m pip install tensorflow[and-cuda]
# Verify the installation:
python3 -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
```

```bash
# There is currently no official GPU support for MacOS.
python3 -m pip install tensorflow
# Verify the installation:
python3 -c "import tensorflow as tf; print(tf.reduce_sum(tf.random.normal([1000, 1000])))"
```

```bash
conda install -c conda-forge cudatoolkit=11.2 cudnn=8.1.0
# Anything above 2.10 is not supported on the GPU on Windows Native
python -m pip install "tensorflow<2.11"
# Verify the installation:
python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
```

```bash
python3 -m pip install tensorflow[and-cuda]
# Verify the installation:
python3 -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
```

```bash
python3 -m pip install tensorflow
# Verify the installation:
python3 -c "import tensorflow as tf; print(tf.reduce_sum(tf.random.normal([1000, 1000])))"
```

```bash
python3 -m pip install tf-nightly
# Verify the installation:
python3 -c "import tensorflow as tf; print(tf.reduce_sum(tf.random.normal([1000, 1000])))"
```

## Requisitos de hardware

Os seguintes dispositivos habilitados para GPU são suportados:

- Placa GPU NVIDIA® com arquiteturas CUDA® 3.5, 5.0, 6.0, 7.0, 7.5, 8.0 e superior. Veja a lista de [placas GPU habilitadas para CUDA®](https://developer.nvidia.com/cuda-gpus) .
- Para GPUs com arquiteturas CUDA® não suportadas, ou para evitar a compilação JIT do PTX, ou para usar versões diferentes das bibliotecas NVIDIA®, consulte o guia [Linux build from source](https://www.tensorflow.org/install/source?hl=pt-br) .
- Os pacotes não contêm código PTX, exceto para a arquitetura CUDA® suportada mais recente; portanto, o TensorFlow falha ao carregar em GPUs mais antigas quando `CUDA_FORCE_PTX_JIT=1` está definido. (Consulte [Compatibilidade de aplicativos](https://docs.nvidia.com/cuda/cuda-c-programming-guide/index.html#application-compatibility) para obter detalhes.)

## requisitos de sistema

- Ubuntu 16.04 ou superior (64 bits)
- macOS 10.12.6 (Sierra) ou superior (64 bits) _(sem suporte de GPU)_
- Windows Native - Windows 7 ou superior (64 bits) _(sem suporte de GPU após TF 2.10)_
- Windows WSL2 - Windows 10 19044 ou superior (64 bits)

## Requisitos de software

- Python 3.9–3.11
- pip versão 19.0 ou superior para Linux (requer suporte para `manylinux2014` ) e Windows. pip versão 20.3 ou superior para macOS.
- Windows Native requer [Microsoft Visual C++ Redistributable para Visual Studio 2015, 2017 e 2019](https://support.microsoft.com/help/2977003/the-latest-supported-visual-c-downloads)

Os seguintes softwares NVIDIA® são necessários apenas para suporte de GPU.

- [Drivers de GPU NVIDIA®](https://www.nvidia.com/drivers) versão 450.80.02 ou superior.
- [Kit de ferramentas CUDA® 11.8](https://developer.nvidia.com/cuda-toolkit-archive) .
- [cuDNNSDK 8.6.0](https://developer.nvidia.com/cudnn) .
- _(Opcional)_ [TensorRT](https://docs.nvidia.com/deeplearning/tensorrt/archives/index.html#trt_7) para melhorar a latência e a taxa de transferência para inferência.

## Instruções passo a passo

### 1. Requisitos do sistema

- Ubuntu 16.04 ou superior (64 bits)

O TensorFlow oferece suporte oficial apenas ao Ubuntu. No entanto, as instruções a seguir também podem funcionar para outras distribuições Linux.

### 2. Configuração da GPU

Você pode pular esta seção se executar o TensorFlow apenas na CPU.

Instale o [driver da GPU NVIDIA,](https://www.nvidia.com/Download/index.aspx) caso ainda não o tenha feito. Você pode usar o seguinte comando para verificar se ele está instalado.

```bash
nvidia-smi
```

### 3. Instale o TensorFlow

O TensorFlow requer uma versão recente do pip, portanto, atualize a instalação do pip para ter certeza de que está executando a versão mais recente.

```bash
pip install --upgrade pip
```

Em seguida, instale o TensorFlow com pip.

```bash
# For GPU users
pip install tensorflow[and-cuda]
# For CPU users
pip install tensorflow
```

### 4. Verifique a instalação

Verifique a configuração da CPU:

```bash
python3 -c "import tensorflow as tf; print(tf.reduce_sum(tf.random.normal([1000, 1000])))"
```

Se um tensor for retornado, você instalou o TensorFlow com sucesso.

Verifique a configuração da GPU:

```bash
python3 -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
```

Se uma lista de dispositivos GPU for retornada, você instalou o TensorFlow com êxito.

### 1\. Requisitos do sistema

- macOS 10.12.6 (Sierra) ou superior (64 bits)

Atualmente não há suporte oficial de GPU para executar o TensorFlow no MacOS. As instruções a seguir são para execução na CPU.

### 2\. Verifique a versão do Python

Verifique se o seu ambiente Python já está configurado:

```bash
python3 --version
python3 -m pip --version
```

### 3\. Instale o TensorFlow

O TensorFlow requer uma versão recente do pip, portanto, atualize a instalação do pip para ter certeza de que está executando a versão mais recente.

```bash
pip install --upgrade pip
```

Em seguida, instale o TensorFlow com pip.

```bash
pip install tensorflow
```

### 4\. Verifique a instalação

```bash
python3 -c "import tensorflow as tf; print(tf.reduce_sum(tf.random.normal([1000, 1000])))"
```

Se um tensor for retornado, você instalou o TensorFlow com sucesso.

## 1\. Requisitos do sistema

- Windows 7 ou superior (64 bits)

### 2\. Instale o Microsoft Visual C++ Redistribuível

Instale o _Microsoft Visual C++ Redistributable para Visual Studio 2015, 2017 e 2019_ . A partir da versão TensorFlow 2.1.0, o arquivo `msvcp140_1.dll` é necessário neste pacote (que pode não ser fornecido em pacotes redistribuíveis mais antigos). O redistribuível vem com _o Visual Studio 2019_ , mas pode ser instalado separadamente:

1. Vá para [downloads do Microsoft Visual C++](https://support.microsoft.com/help/2977003/the-latest-supported-visual-c-downloads) .
2. Role a página para baixo até a seção _Visual Studio 2015, 2017 e 2019_ .
3. Baixe e instale o _Microsoft Visual C++ Redistributable para Visual Studio 2015, 2017 e 2019_ para sua plataforma.

Certifique-se de [que caminhos longos estejam habilitados](https://superuser.com/questions/1119883/windows-10-enable-ntfs-long-paths-policy-option-missing) no Windows.

### 3\. Instale o Miniconda

[Miniconda](https://docs.conda.io/en/latest/miniconda.html) é a abordagem recomendada para instalar o TensorFlow com suporte a GPU. Ele cria um ambiente separado para evitar a alteração de qualquer software instalado em seu sistema. Esta também é a maneira mais fácil de instalar o software necessário, especialmente para a configuração da GPU.

Baixe o [instalador do Windows Miniconda](https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe) . Clique duas vezes no arquivo baixado e siga as instruções na tela.

### 4\. Crie um ambiente conda

Crie um novo ambiente conda denominado [`tf`](https://www.tensorflow.org/api_docs/python/tf?hl=pt-br) com o seguinte comando.

```bash
conda create --name tf python=3.9
```

Você pode desativá-lo e ativá-lo com os seguintes comandos.

```bash
conda deactivate
conda activate tf
```

Certifique-se de que esteja ativado para o restante da instalação.

### 5\. Configuração da GPU

Você pode pular esta seção se executar o TensorFlow apenas na CPU.

Primeiro instale [o driver da GPU NVIDIA,](https://www.nvidia.com/Download/index.aspx) caso ainda não o tenha feito.

Em seguida, instale o CUDA, cuDNN com conda.

```bash
conda install -c conda-forge cudatoolkit=11.2 cudnn=8.1.0
```

### 6\. Instale o TensorFlow

O TensorFlow requer uma versão recente do pip, portanto, atualize a instalação do pip para ter certeza de que está executando a versão mais recente.

```bash
pip install --upgrade pip
```

Em seguida, instale o TensorFlow com pip.

```bash
# Anything above 2.10 is not supported on the GPU on Windows Native
pip install "tensorflow<2.11"
```

### 7\. Verifique a instalação

Verifique a configuração da CPU:

```bash
python -c "import tensorflow as tf; print(tf.reduce_sum(tf.random.normal([1000, 1000])))"
```

Se um tensor for retornado, você instalou o TensorFlow com sucesso.

Verifique a configuração da GPU:

```bash
python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
```

Se uma lista de dispositivos GPU for retornada, você instalou o TensorFlow com êxito.

### 1\. Requisitos do sistema

- Windows 10 19044 ou superior (64 bits). Isso corresponde ao Windows 10 versão 21H2, atualização de novembro de 2021.

Consulte os seguintes documentos para:

- [Baixe a atualização mais recente do Windows 10](https://www.microsoft.com/software-download/windows10) .
- [Instale WSL2](https://docs.microsoft.com/windows/wsl/install)
- [Configure o suporte de GPU NVIDIA® em WSL2](https://docs.nvidia.com/cuda/wsl-user-guide/index.html)

### 2\. Configuração da GPU

Você pode pular esta seção se executar o TensorFlow apenas na CPU.

Instale o [driver da GPU NVIDIA](https://www.nvidia.com/Download/index.aspx) , caso ainda não o tenha feito. Você pode usar o seguinte comando para verificar se ele está instalado.

```bash
nvidia-smi
```

### 3\. Instale o TensorFlow

O TensorFlow requer uma versão recente do pip, portanto, atualize a instalação do pip para ter certeza de que está executando a versão mais recente.

```bash
pip install --upgrade pip
```

Em seguida, instale o TensorFlow com pip.

```bash
# For GPU users
pip install tensorflow[and-cuda]
# For CPU users
pip install tensorflow
```

### 4\. Verifique a instalação

Verifique a configuração da CPU:

```bash
python3 -c "import tensorflow as tf; print(tf.reduce_sum(tf.random.normal([1000, 1000])))"
```

Se um tensor for retornado, você instalou o TensorFlow com sucesso.

Verifique a configuração da GPU:

```bash
python3 -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
```

Se uma lista de dispositivos GPU for retornada, você instalou o TensorFlow com êxito.

## Localização do pacote

Alguns mecanismos de instalação exigem o URL do pacote TensorFlow Python. O valor que você especifica depende da sua versão do Python.

| Versão | URL |
| --- | --- |
| Linux |
| Suporte para GPU Python 3.9 | [https://storage.googleapis.com/tensorflow/linux/gpu/tensorflow-2.15.0-cp39-cp39-manylinux\_2\_17\_x86\_64.manylinux2014\_x86\_64.whl](https://storage.googleapis.com/tensorflow/linux/gpu/tensorflow-2.15.0-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.whl) |
| Somente CPU Python 3.9 | [https://storage.googleapis.com/tensorflow/linux/cpu/tensorflow\_cpu-2.15.0-cp39-cp39-manylinux\_2\_17\_x86\_64.manylinux2014\_x86\_64.whl](https://storage.googleapis.com/tensorflow/linux/cpu/tensorflow_cpu-2.15.0-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.whl) |
| Suporte para GPU Python 3.10 | [https://storage.googleapis.com/tensorflow/linux/gpu/tensorflow-2.15.0-cp310-cp310-manylinux\_2\_17\_x86\_64.manylinux2014\_x86\_64.whl](https://storage.googleapis.com/tensorflow/linux/gpu/tensorflow-2.15.0-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl) |
| Python 3.10 somente CPU | [https://storage.googleapis.com/tensorflow/linux/cpu/tensorflow\_cpu-2.15.0-cp310-cp310-manylinux\_2\_17\_x86\_64.manylinux2014\_x86\_64.whl](https://storage.googleapis.com/tensorflow/linux/cpu/tensorflow_cpu-2.15.0-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl) |
| Suporte para GPU Python 3.11 | [https://storage.googleapis.com/tensorflow/linux/gpu/tensorflow-2.15.0-cp311-cp311-manylinux\_2\_17\_x86\_64.manylinux2014\_x86\_64.whl](https://storage.googleapis.com/tensorflow/linux/gpu/tensorflow-2.15.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl) |
| Somente CPU Python 3.11 | [https://storage.googleapis.com/tensorflow/linux/cpu/tensorflow\_cpu-2.15.0-cp311-cp311-manylinux\_2\_17\_x86\_64.manylinux2014\_x86\_64.whl](https://storage.googleapis.com/tensorflow/linux/cpu/tensorflow_cpu-2.15.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl) |
| macOS (somente CPU) |
| Pitão 3.9 | [https://storage.googleapis.com/tensorflow/mac/cpu/tensorflow-2.15.0-cp39-cp39-macosx\_10\_15\_x86\_64.whl](https://storage.googleapis.com/tensorflow/mac/cpu/tensorflow-2.15.0-cp39-cp39-macosx_10_15_x86_64.whl) |
| Pitão 3.10 | [https://storage.googleapis.com/tensorflow/mac/cpu/tensorflow-2.15.0-cp310-cp310-macosx\_10\_15\_x86\_64.whl](https://storage.googleapis.com/tensorflow/mac/cpu/tensorflow-2.15.0-cp310-cp310-macosx_10_15_x86_64.whl) |
| Pitão 3.11 | [https://storage.googleapis.com/tensorflow/mac/cpu/tensorflow-2.15.0-cp311-cp311-macosx\_10\_15\_x86\_64.whl](https://storage.googleapis.com/tensorflow/mac/cpu/tensorflow-2.15.0-cp311-cp311-macosx_10_15_x86_64.whl) |
| janelas |
| Somente CPU Python 3.9 | [https://storage.googleapis.com/tensorflow/windows/cpu/tensorflow\_cpu-2.15.0-cp39-cp39-win\_amd64.whl](https://storage.googleapis.com/tensorflow/windows/cpu/tensorflow_cpu-2.15.0-cp39-cp39-win_amd64.whl) |
| Python 3.10 somente CPU | [https://storage.googleapis.com/tensorflow/windows/cpu/tensorflow\_cpu-2.15.0-cp310-cp310-win\_amd64.whl](https://storage.googleapis.com/tensorflow/windows/cpu/tensorflow_cpu-2.15.0-cp310-cp310-win_amd64.whl) |
| Somente CPU Python 3.11 | [https://storage.googleapis.com/tensorflow/windows/cpu/tensorflow\_cpu-2.15.0-cp311-cp311-win\_amd64.whl](https://storage.googleapis.com/tensorflow/windows/cpu/tensorflow_cpu-2.15.0-cp311-cp311-win_amd64.whl) |
