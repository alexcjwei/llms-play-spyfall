def get_question_examples(is_spy: bool):
        return f"""Good question example:
As the Archer in the Crusader Army, Isaac asks Juan: "Juan, when do we get paid — is it at the beginning of the month, or the end?"
Explanation: This does not say terms specific to the Crusader Army location like things about religion, faith, or knights.

Bad question example:
As the Zookeeper at the Zoo, Maria asks Anna: "Anna, how's the feeding schedule working out with the new management?"
Explanation: This heavily implies to the spy that the location is Zoo. The spy could now win by guessing the location.
"""

def get_answer_examples(is_spy: bool):
        return f"""Good answer example:
As the Knight in the Crusader Army, Juan was asked: "Juan, when do we get paid — is it at the beginning of the month, or the end?"
Juan responds: "Who knows? We'll get paid whenever the commander feels like paying us." 
Explanation: This response is brief could apply in other locations besides Crusader Army like Military Base, Submarine, Pirate Ship, and potentially others. It reveals minimal information to the spy while satisfying the questioner that Juan is not the spy.

Bad answer example:
As the Zookeeper at the Zoo, Maria asks asked: "Maria, what's that smell?"
Maria responds: "Oh, you know how it is with all the different... residents here. Some areas are definitely more pungent than others, especially near the large mammal enclosures."
Explanation: This heavily implies to the spy that the location is Zoo. The spy could now win by guessing the location.
"""
