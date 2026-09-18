from backend.training.enrichment import extract_concepts, extract_relations, qa_cards

def test_concepts_and_cards_are_richer_than_title_only():
    text='بايثون لغة برمجة سهلة. تستخدم في تحليل البيانات والذكاء الاصطناعي. لأن مكتباتها كثيرة فهي مناسبة للتعلم السريع.'
    concepts=extract_concepts(text)
    cards=qa_cards(text,'بايثون')
    assert 'بايثون' in concepts
    assert len(cards)>=2

def test_relation_extraction():
    text='الأمن السيبراني يهدف إلى حماية الأنظمة والبيانات من الهجمات.'
    rel=extract_relations(text)
    assert rel and rel[0]['type']=='purpose'
