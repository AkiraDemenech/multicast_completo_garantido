# Multicast Confiável
Garante o envio completo
(ou pelo menos tenta)

> Como iniciar: 

- Identificar pelo endereço de IP (recomendado):

		python3 confia.py <arquivo_informando_os_componentes> --address	<ip>
		
- Identificar pelo nome (é necessário que o endereço de IP esteja no arquivo dos componentes do grupo):
		
		python3 confia.py <arquivo_informando_os_componentes> --host	<nome>
		
Os componentes do grupo estão informados no arquivo como:

		<ip> <nome>	
		<ip> <nome>	
		<ip> <nome>	
		
O formato para informar endereço IP é 
	
		<endereço>:<porta>
**Exemplos**: 

		localhost:8080
		127.0.0.1:65432	
		
**Outras opções disponíveis**:
		
-	Tempo de atraso de resposta:	
	
		--delay <segundos: float>	

- Período de heartbeat:

		--heartbeat <segundos: float>
- Intervalo para retransmissão de mensagens:	

		--retransmission <segundos: float>

- Tempo para detecção de falha:	

		--timeout <segundos: float>

- Quantidade de cópias enviadas por fileira:	

		--redundancy <cópias: int>
		
- Quantidade máxima de fileiras para dividir o grupo: 

		--max_rows <fileiras: int>
		
_Todo argumento que não for precedido por uma das opções válidas será interpretado como um nome de arquivo e terá suas linhas lidas como endereços de componentes do grupo._	

_Caso algum arquivo acessível pelo programa tenha o mesmo nome que uma dessas opções, ele será lido e a opção será ignorada._
	
__Você pode inserir quantos traços quiser no começo de cada opção para diferenciá-las de quaisquer arquivos no diretório de execução.__

__Pode ser adicionada qualquer quantidade de arquivos, inclusive nenhum.__	

>> Comandos:

- Exibe os comandos disponíves	

		help 

- Sai do programa 		

		exit
		
- Envia uma mensagem para todos os componentes do grupo e aguarda confirmações individuais de todos eles.

		direct "<mensagem>"

	A mensagem deve ser um literal válido na sintaxe Python, podendo ser string, tupla, lista, dicionário, inteiro ou ponto flutuante, por exemplo.	
		
- Envia uma mensagem para os primeiros componentes de cada fileira e aguarda confirmações de todas as fileiras.		

		row "<mensagem>"
		
	A quantidade de cópias por fileira pode ser alterada com set_redundancy e a quantidade máxima de fileiras pode ser alterada com set_max_rows
		
	A mensagem deve ser um literal válido na sintaxe Python, podendo ser string, tupla, lista, dicionário, inteiro ou ponto flutuante, por exemplo.
	
 - Envia uma mensagem para os pais de cada árvore e aguarda confirmações de todas elas.
 
		tree "<mensagem>"	
		
	A quantidade de cópias por árvore pode ser alterada com set_redundancy e a quantidade máxima de árvores pode ser alterada com set_max_rows
	
	A mensagem deve ser um literal válido na sintaxe Python, podendo ser string, tupla, lista, dicionário, inteiro ou ponto flutuante, por exemplo.	

- Adiciona um novo componente ao grupo, caso ainda não estivesse.

		add "<ip>",<porta>		
		
- Altera o nome do host		

		rename "<nome>"
		
- Altera o atraso para o envio de mensagens		

		delay <segundos>	
		
- Altera o período de tempo entre os heartbeats

		heartbeat <segundos>
		
	Caso seja 0, desativa o heartbeat permanentemente

- Pausa o heartbeat		

		pause 
		
- Retoma o heartbeat 		

		play 
		
- Mostra o último heartbeat de todos os componentes do grupo ativos		

		status
		
- Altera a quantidade de cópias enviadas por fileira no multicast em fileiras (row)		

		set_redundancy <cópias>
		
	Essa quantidade é mesma que cada componente da fileira enviará para os próximos
	
- Altera a quantidade máxima de fileiras para dividir o grupo no multicast em fileiras (row)				

		set_max_rows <fileiras>
		
- Altera o intervalo para retransmissão de mensagens		

		set_reliable_interval <segundos>
		
- Altera o tempo para detecção de falha		

		set_reliable_timeout <segundos>
		
		
		
		