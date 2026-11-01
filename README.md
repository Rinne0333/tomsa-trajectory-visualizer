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

A Global View apresenta a missão num mapa e permite consultar os dados de cada instante.

### Funcionalidades

- Mapa OpenStreetMap com uma cor por robot.
- Percursos passados, posições atuais e percursos futuros registados.
- Slider para avançar e retroceder, com passo de 0,1 s.
- Reprodução e pausa, com velocidades de 1×, 5×, 10×, 25×, 50× e 100×.
- Relógio `HH:MM:SS` e duração total da missão.
- Botão **Enquadrar missão** para repor a vista geral.
- Painel lateral que pode ser ocultado.
- Consulta de coordenadas, distâncias, matrizes de rotação e velocidades.
- Seleção de um robot ou de todos nos painéis de coordenadas e velocidades.

### Módulos e funções

Os módulos seguintes encontram-se em `global_plot/`:

| Módulo | Funções principais | Responsabilidade |
|---|---|---|
| `data_loader.py` | `load_robot_log()` | Ler e validar os CSV |
| `replay.py` | `prepare_replay_data()`, `get_replay_history()` | Criar o tempo comum e selecionar os históricos |
| `map_view.py` | `simplify_path()`, `get_robot_parts()`, `build_trajectory_map()`, `update_trajectory_map()` | Preparar e atualizar trajetórias e posições |
| `mission_table.py` | `build_position_rows()` | Preparar coordenadas, estados e tempos |
| `distances.py` | `horizontal_distance_m()`, `build_distance_rows()` | Calcular distâncias entre pares |
| `orientation.py` | `quaternion_to_matrix()`, `check_rotation_matrix()` | Converter quaterniões e validar matrizes de rotação|
| `orientation_view.py` | `build_rotation_panels()` | Construir os painéis das matrizes |

A `main` junta estes módulos, constrói a interface e liga os controlos aos callbacks.

O fluxo dos dados é: **carregar CSV → validar → ordenar e preparar o tempo → selecionar histórico → calcular informação → atualizar a interface**.

### Tempo da missão e replay

Os campos de tempo são reunidos em nanossegundos:

```python
timestamp_ns = header_stamp_secs * 1_000_000_000 + header_stamp_nsecs
```

Os registos são ordenados, mantendo a ordem original quando existem timestamps iguais. O primeiro registo entre todos os robots define o início comum:

```python
mission_time_s = (timestamp_ns - mission_start_ns) / 1_000_000_000
```

Isto preserva os desfasamentos entre robots. A duração da missão é o maior tempo encontrado nos logs.

Para um instante selecionado, `get_replay_history()` mantém os registos com `mission_time_s <= selected_time_s`. A posição atual é o último registo disponível. Não existe interpolação: a posição mantém-se entre duas medições.

Durante a reprodução, `dcc.Interval` solicita atualizações a cada 250 ms. O avanço usa o tempo real decorrido, medido por `time.monotonic()`:

```python
novo_tempo = tempo_atual + tempo_real_decorrido * velocidade_anterior
```

O `dcc.Store` guarda `playing`, `last_tick` e `speed`. Uma alteração de velocidade aplica-se ao intervalo seguinte. Ao chegar ao fim, a reprodução para; premir Reproduzir reinicia a missão a partir de zero.

### Mapa e trajetórias

Nestes logs, `pose.pose.position.x` é interpretado como **latitude** e `pose.pose.position.y` como **longitude**, em graus.

O fundo é escolhido com `"style": "open-street-map"`. O navegador carrega a cartografia e o Plotly sobrepõe os percursos. 

| Robot | Cor |
|---|---|
| Robot 1 | Azul — `#2563eb` |
| Robot 4 | Laranja — `#ea580c` |
| Robot 7 | Roxo — `#9333ea` |

Cada robot tem uma linha contínua para o passado, um marcador com nome para a posição atual e uma linha tracejada para o futuro. O percurso futuro vem do log completo; não é uma previsão.

`simplify_path()` reduz cada linha a um máximo de 1000 pontos por omissão, preservando os extremos. A redução afeta apenas o desenho; os cálculos e a posição atual usam os dados completos.

`mission_camera()` estima o centro e o zoom a partir dos limites da missão em Web Mercator. `build_initial_map()` aplica esse enquadramento e o estilo, com opacidade `0.18` para o passado e tamanho `13` para os marcadores atuais.

As atualizações normais usam um `Patch` para modificar apenas os dados necessários. `uirevision` permite conservar o enquadramento escolhido pelo utilizador. **Enquadrar missão** reconstrói a figura e repõe o centro, zoom, orientação e inclinação da vista geral.

### Painel de coordenadas

Apresenta latitude, longitude, instante e idade da medição.

```python
age_s = max(0.0, selected_time_s - record_time_s)
```

Por exemplo, aos 15 s de replay, uma posição registada aos 12 s tem 3 s de idade.

| Estado | Significado |
|---|---|
| A aguardar | Ainda não existe um registo para o instante escolhido |
| Dados disponíveis | Existe uma posição disponível |
| Log terminado | O tempo selecionado ultrapassou o último registo do robô |

O estado interno `Em reprodução` é apresentado como `Dados disponíveis`: descreve a disponibilidade dos dados, independentemente de Play/Pause. Após o fim do log, a última posição mantém-se e a idade aumenta.

### Painel de distâncias

Mostra uma distância por par: **1–4, 1–7 e 4–7**. Cada par é gerado uma única vez com `combinations()`.

A fórmula de Haversine calcula a distância horizontal aproximada entre latitudes e longitudes, usando uma Terra esférica de raio `6_371_008.8 m`. O cálculo limita o valor intermédio ao intervalo `[0, 1]` para evitar erros numéricos.

### Painel de matrizes de rotação

Os quaterniões são lidos na ordem **`[x, y, z, w]`**. A conversão rejeita componentes não finitos e o quaternião nulo, ajusta a escala para evitar overflow, normaliza e constrói uma matriz de rotação ativa 3×3.

A validação verifica se a transposta multiplicada pela matriz é aproximadamente a identidade e se o determinante é aproximadamente +1, com uma tolerância `10e-10`.

O painel apresenta a matriz com quatro casas decimais, o instante, o determinante com seis casas e o resultado da validação. O arredondamento é apenas visual.

### Painel de velocidades

Apresenta a última medição disponível:

- Magnitude da velocidade linear 3D: `sqrt(vx² + vy² + vz²)`.
- Componentes X, Y e Z da velocidade linear, em m/s.
- Componentes X, Y e Z da velocidade angular, em rad/s.
- Referencial reportado em `child_frame_id`, instante e idade da medição.

Os valores vêm do log, sem cálculo por diferenças de posição. Alterar a velocidade do replay não altera a velocidade física apresentada.

### Interface e callbacks

`Input` desencadeia uma atualização; `State` fornece um valor sem a desencadear; `Output` recebe o resultado. Os resultados são devolvidos pela ordem dos Outputs.

| Callback | Entrada | Atualização |
|---|---|---|
| `update_coordinate_panel()` | Tempo ou robot selecionado | Coordenadas |
| `update_velocity_panel()` | Tempo ou robot selecionado | Velocidades |
| `toggle_mission_sidebar()` | Clique em Ocultar/Mostrar painel | Visibilidade, largura e botão do painel |
| `select_sidebar_section()` | Secção selecionada | Informação visível no painel lateral |
| `update_mission_view()` | Tempo ou Enquadrar missão | Relógio, mapa, matrizes e distâncias |
| `select_view()` | Vista selecionada | Global View ou Local View |
| `control_replay()` | Play/Pause, temporizador ou velocidade | Slider, temporizador, botão e estado |

`control_replay()` consulta o slider e o estado com `State`, ignora a chamada inicial com `prevent_initial_call=True` e identifica o evento através de `ctx`.

Os contentores ocultos permanecem na página para os callbacks continuarem a encontrar os seus destinos. Ocultar uma secção não suspende os seus cálculos. Selecionar um robô nas coordenadas ou velocidades não atualiza o mapa.

| Função auxiliar na main | Responsabilidade |
|---|---|
| `format_mission_time()` | Formatar o relógio, sem reiniciar após 24 horas |
| `robot_label()` | Apresentar o nome com a cor do robô |
| `polish_cards()` | Uniformizar o aspeto dos painéis e os títulos |
| `build_coordinate_panel()` | Construir os painéis de coordenadas sem Z |
| `build_distance_panel()` | Construir um painel por par |
| `build_velocity_panel()` | Construir os painéis de velocidades |
| `build_rotation_panels()` | Aplicar o estilo aos painéis de orientação |

`polish_cards()` altera os componentes recebidos. Quando recebe nomes, estes devem corresponder à ordem dos painéis, cujo primeiro elemento deve ser o título.

A função `update_table()` tem o decorador de callback comentado; não controla os painéis de coordenadas ativos.


## Local View

Controlo da visão local pode ser feito através de: 

- Dropdown no topo do ecrã, onde se escolhe um robô para observar.
- Painel na esquerda do ecrã, onde se consegue observar os valores de profundidade relativa e distancia entre os robôs que estejam na sua vizinhança.
- Barra de scroll em baixo para dar playback á missão inteira do robô.