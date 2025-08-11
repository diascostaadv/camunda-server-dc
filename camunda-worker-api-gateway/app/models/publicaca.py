# execucao = {
#     "_id": str, 
#     "data_inicio": datetime, 
#     "data_fim": Optional[datetime], 
#     "status": Literal["running", "completed", "error", "cancelled"],
#     "total_encontradas": int,
# }

# publicacao = {
#     "_id_execucao": str,
#     "numero_processo": str,
#     "data_publicacao": str,
#     "texto_publicacao": str,
#     "fonte": str,
#     "tribunal": str,
#     "instancia": str,
#     "descricao_diario": Optional[str],
#     "uf_publicacao": Optional[str],
#     "cod_publicacao": int,
# }

# collection_publicacao.find_one({"_id_execucao": execucao["_id"]})