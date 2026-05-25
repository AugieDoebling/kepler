from .database_client import get_msg_scores, get_messages

def search_memory(keywords: list[str], limit: int = 10):

   total_msg_scores = {}

   for key in keywords:
      msg_scores = get_msg_scores(key)
      for msg_id, score in msg_scores:
         if not msg_id in total_msg_scores:
            total_msg_scores[msg_id] = 0
         total_msg_scores[msg_id] += score


   result_ids = sorted(total_msg_scores.keys(), key=lambda msg_id: total_msg_scores[msg_id], reverse=True)[:limit]
   return get_messages(result_ids)