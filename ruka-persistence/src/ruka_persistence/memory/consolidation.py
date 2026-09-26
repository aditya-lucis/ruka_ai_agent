from typing import List, Tuple
from ruka_persistence.memory.types import SemanticFact

DUPLICATE_JACCARD = 0.8
MAX_MERGE_CONFIDENCE = 0.85
CONFLICT_CONFIDENCE_MARGIN = 0.2

def same_triple(t1: tuple, t2: tuple) -> bool:
    return (t1[0].lower() == t2[0].lower() and 
            t1[1].lower() == t2[1].lower())

def jaccard(s1: str, s2: str) -> float:
    s1_words = set(s1.lower().split())
    s2_words = set(s2.lower().split())
    if not s1_words or not s2_words:
        return 0.0
    return len(s1_words & s2_words) / len(s1_words | s2_words)

class ConsolidationPipeline:
    """Pipeline konsolidasi memori 8-tahap (Listing 4.0 & 4.1)."""
    
    def run(self, raw_events: list, existing_facts: list[SemanticFact]) -> dict:
        """Tahap 1-8 konsolidasi (placeholder for structural tests)."""
        # Dalam praktek nyata, ini memanggil fungsi-fungsi LLM dan ekstraksi
        # Namun test kita berfokus pada logika dedup dan konflik
        pass

    def dedup_and_conflicts(self, new_facts: list[SemanticFact],
                            existing_facts: list[SemanticFact]
                            ) -> tuple[list[SemanticFact],
                                       list[SemanticFact],
                                       list[SemanticFact]]:
        """Tahap 6-7: pisahkan duplikat & konflik dari fakta baru.
        Asumsi penting: (subject, predicate) dipakai seolah PREDIKAT FUNGSIONAL.
        """
        merged: list[SemanticFact] = []
        conflicts: list[SemanticFact] = []
        unique_new: list[SemanticFact] = []
        
        pool = list(existing_facts)
        
        for nf in new_facts:
            placed = False
            for old in list(pool):
                if same_triple((nf.subject, nf.predicate, nf.value),
                               (old.subject, old.predicate, old.value)):
                    similarity = jaccard(nf.value, old.value)
                    
                    if similarity >= DUPLICATE_JACCARD:
                        # DUPLICATE: perkuat yang lama
                        old.confidence = round(
                            max(old.confidence,
                                min(MAX_MERGE_CONFIDENCE,
                                    old.confidence + 0.10)), 4)
                        merged.append(old)
                        nf.note = "merged_as_duplicate"
                        placed = True
                        break
                        
                    # KONFLIK: subjek-predikat sama, nilai beda
                    if (nf.confidence - old.confidence
                            >= CONFLICT_CONFIDENCE_MARGIN):
                        old.superseded_by = nf.fact_id
                        conflicts.append(old)
                        nf.version = old.version + 1
                        nf.note = f"supersedes:{old.fact_id}@v{old.version}"
                        unique_new.append(nf)
                        pool.remove(old)
                        pool.append(nf)     # pemenang bisa diuji lagi
                        placed = True
                        break
                        
                    # Konflik dengan margin tipis: TIDAK diputus paksa
                    nf.note = "conflict_unresolved_low_margin"
                    conflicts.append(nf)
                    pool.append(nf)          # tetap bisa dicocokkan
                    placed = True
                    break
                    
            if not placed:
                unique_new.append(nf)
                pool.append(nf)
                
        return merged, conflicts, unique_new
