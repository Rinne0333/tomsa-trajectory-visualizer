# TOMSA TRAJECTORY VISUALIZER

Aplicação para visualizar e reproduzir trajetórias de robôs a partir de registos CSV. A interface permite escolher entre **Global View** e **Local View**.

## Índice

- [Instalação](#instalação)
- [Execução](#execução)
- [Organização do projeto](#organização-do-projeto)
- [Dados de entrada](#dados-de-entrada)
- [Global View](#global-view)
- [Local View](#local-view)


## Instalação

Na raiz do projeto, criar o ambiente virtual:

```bash
python -m venv venv
```

Ativar o ambiente antes de instalar as dependências:

```bash
source venv/bin/activate
```

Instalar as dependências do projeto:

```bash
pip install -r requirements.txt
```

## Execução

O código encontra-se em **`src/trajectory-visualizer`**.

Na raiz do projeto, ativa o ambiente:

```bash
source venv/bin/activate
```

Inicia a aplicação:

```bash
python src/trajectory-visualizer/__main__.py
```

Abre o endereço indicado no terminal. No seletor superior, escolhe **Visão Global** ou **Visão Local**. A aplicação começa com a Visão Local selecionada.

O arranque usa `app.run(debug=True)` para desenvolvimento local.

## Organização do projeto

Os caminhos seguintes são relativos à raiz do projeto:

| Caminho | Conteúdo |
|---|---|
| `requirements.txt` | Dependências Python |
| `data/` | Registos CSV dos robots |
| `src/trajectory-visualizer/__main__.py` | Arranque, interface e callbacks |
| `src/trajectory-visualizer/global_plot/` | Módulos da Global View |
| `src/trajectory-visualizer/pov-plot/` | Recursos da Local View |

A aplicação procura `robot1_s1.csv`, `robot4_s1.csv` e `robot7_s1.csv` em `data/`. A raiz é calculada a partir da localização de `__main__.py`, com `Path(__file__).resolve().parents[2]`.

## Dados de entrada

Cada CSV contém os registos de um robô. Os nomes das colunas devem corresponder aos definidos em `data_loader.py`.

| Grupo | Colunas obrigatórias |
|---|---|
| Tempo e identificação | `Time`, `header.seq`, `header.stamp.secs`, `header.stamp.nsecs`, `header.frame_id`, `child_frame_id` |
| Posição | `pose.pose.position.x`, `pose.pose.position.y`, `pose.pose.position.z` |
| Orientação | `pose.pose.orientation.x`, `pose.pose.orientation.y`, `pose.pose.orientation.z`, `pose.pose.orientation.w` |
| Covariância de pose | `pose.covariance` |
| Velocidade linear | `twist.twist.linear.x`, `twist.twist.linear.y`, `twist.twist.linear.z` |
| Velocidade angular | `twist.twist.angular.x`, `twist.twist.angular.y`, `twist.twist.angular.z` |
| Covariância de velocidade | `twist.covariance` |

O carregamento rejeita ficheiros sem registos, colunas em falta e valores numéricos vazios, não numéricos ou infinitos.

### Bibliotecas utilizadas

| Biblioteca | Utilização |
|---|---|
| Dash | Interface, callbacks, temporizador, estado e atualizações parciais |
| Plotly | Mapa, linhas e marcadores |
| Pandas | Leitura, validação, ordenação e filtragem dos CSV |
| NumPy | Cálculos de distâncias, velocidades e matrizes de rotação |
| Flask | Rotas da aplicação partilhada |
| ThreeJS | Representação tridimensional |

São utilizadas as APIs `go.Scattermap` e `dash.Patch`.

Modelo de robô: [Weaver: Vectored 8 - Thruster ROV / AUV](https://sketchfab.com/3d-models/weaver-vectored-8-thruster-rov-auv-a34c315bae734a2eaae97a2029c0a016)

## Global View

A visão global permite acompanhar a missão dos três robôs num mapa OpenStreetMap através de:

- Mapa com trajetórias passadas, posições atuais e percursos futuros registados, identificando cada robô por uma cor.

- Barra temporal para selecionar um instante, avançar e retroceder na missão.

- Controlos de reprodução e pausa, com velocidades entre 1× e 100× e indicação do tempo da missão.

- Botão «Enquadrar missão» para ajustar o mapa aos percursos completos.

- Painel lateral que pode ser ocultado e permite consultar:
  - **Coordenadas:** latitude, longitude, instante e idade da medição.
  - **Distâncias:** distância horizontal aproximada entre cada par de robôs.
  - **Matrizes de rotação:** conversão dos quaterniões e verificação da validade matemática das matrizes.
  - **Velocidades:** magnitude da velocidade linear, componentes lineares e angulares e referencial indicado no log.

- Seleção de um robô ou de todos nos painéis de coordenadas e velocidades.


## Local View

Controlo da visão local pode ser feito através de: 

- Dropdown no topo do ecrã, onde se escolhe um robô para observar.
- Painel na esquerda do ecrã, onde se consegue observar os valores de profundidade relativa e distancia entre os robôs que estejam na sua vizinhança.
- Barra de scroll em baixo para dar playback á missão inteira do robô.