"""
Validation module for Value Proposition Canvas items.
Checks for quality, specificity, and independence of pain/gain points.
"""

from typing import List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


class QualityValidator:
    """Validates the quality and independence of canvas items."""

    # Minimum character length for meaningful entries
    MIN_CHAR_LENGTH = 20

    # Maximum similarity threshold (items above this are considered too similar)
    SIMILARITY_THRESHOLD = 0.8

    # Minimum requirements
    MIN_PAIN_POINTS = 7
    MIN_GAIN_POINTS = 8

    # Vague-word ratio threshold for specificity check
    VAGUE_WORD_RATIO = 0.2

    # Overall canvas score weighting (must sum to 1.0)
    JOB_WEIGHT = 0.30
    PAIN_WEIGHT = 0.35
    GAIN_WEIGHT = 0.35

    # Synonym clusters for hybrid relevance scoring (substring matching)
    SYNONYM_CLUSTERS = [
        {'process', 'workflow', 'pipeline', 'procedure', 'system', 'method', 'approach'},
        {'monitor', 'track', 'dashboard', 'alert', 'observ', 'metric', 'measure', 'report'},
        {'time', 'speed', 'fast', 'slow', 'quick', 'delay', 'wait', 'long', 'duration', 'hour'},
        {'improve', 'enhance', 'better', 'optim', 'upgrad', 'refin', 'boost'},
        {'automat', 'manual', 'script', 'tool', 'efficien'},
        {'deploy', 'release', 'build', 'ship', 'rollout', 'ci/cd', 'infrastructur', 'server', 'environment'},
        {'quality', 'reliable', 'bug', 'error', 'fail', 'stable', 'robust', 'recover', 'heal', 'resilien'},
        {'team', 'collaborat', 'communicat', 'stakeholder', 'colleague'},
        {'cost', 'budget', 'expens', 'resource', 'invest'},
        {'risk', 'secur', 'vulnerab', 'threat', 'protect', 'safe'},
        {'customer', 'user', 'client', 'experience', 'satisf'},
        {'document', 'runbook', 'guide', 'instruct', 'onboard'},
        {'plan', 'schedule', 'deadline', 'milestone', 'priorit', 'goal'},
        {'data', 'analyt', 'insight', 'statist', 'number'},
        {'learn', 'train', 'skill', 'knowledge', 'expert', 'competenc'},
    ]

    # Stopwords for Jaccard stem scoring
    STOPWORDS = frozenset({
        'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'can', 'shall', 'to', 'of', 'in', 'for',
        'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through', 'during',
        'before', 'after', 'above', 'below', 'between', 'and', 'but', 'or',
        'not', 'no', 'nor', 'so', 'yet', 'both', 'each', 'few', 'more',
        'most', 'other', 'some', 'such', 'than', 'too', 'very', 'just',
        'about', 'up', 'out', 'if', 'then', 'that', 'this', 'it', 'its',
        'my', 'our', 'your', 'their', 'i', 'we', 'you', 'they', 'he', 'she',
    })

    def __init__(self):
        pass

    def validate_job_description(self, description: str) -> dict:
        """
        Validate the job description for completeness and quality.

        Returns:
            dict with 'valid', 'score', 'feedback', and 'suggestions'
        """
        feedback = []
        suggestions = []
        score = 0

        # Check minimum length
        if len(description.strip()) < 50:
            feedback.append("Job description is too short. Please provide more detail.")
            suggestions.append("Describe the specific task or goal the customer is trying to accomplish.")
        else:
            score += 25

        # Check for action words
        action_words = ['want', 'need', 'try', 'seek', 'achieve', 'accomplish', 'complete',
                       'solve', 'find', 'get', 'make', 'create', 'improve', 'reduce']
        has_action = any(word in description.lower() for word in action_words)
        if has_action:
            score += 25
        else:
            feedback.append("Consider adding what action the customer wants to take.")
            suggestions.append("Use action verbs like 'achieve', 'accomplish', 'solve', or 'improve'.")

        # Check for context words
        context_words = ['when', 'while', 'during', 'because', 'so that', 'in order to']
        has_context = any(word in description.lower() for word in context_words)
        if has_context:
            score += 25
        else:
            suggestions.append("Add context about when or why this job needs to be done.")

        # Check for specificity (avoiding generic terms)
        generic_terms = ['things', 'stuff', 'something', 'anything', 'everything']
        is_specific = not any(term in description.lower() for term in generic_terms)
        if is_specific:
            score += 25
        else:
            feedback.append("Try to be more specific. Avoid vague terms like 'things' or 'something'.")

        return {
            'valid': len(feedback) == 0,
            'score': min(score, 100),
            'feedback': feedback,
            'suggestions': suggestions
        }

    def validate_item_quality(self, item: str, item_type: str = "point") -> dict:
        """
        Validate a single pain or gain point for quality.

        Returns:
            dict with 'valid', 'score', 'feedback'
        """
        feedback = []
        score = 0

        # Check minimum length
        if len(item.strip()) < self.MIN_CHAR_LENGTH:
            feedback.append(f"This {item_type} is too brief. Please elaborate.")
        else:
            score += 50

        # Check for specificity
        vague_words = ['bad', 'good', 'nice', 'problem', 'issue', 'thing', 'stuff']
        words = item.lower().split()
        vague_count = sum(1 for w in words if w in vague_words)

        if vague_count > len(words) * self.VAGUE_WORD_RATIO:
            feedback.append("Try to be more specific about the pain or gain.")
        else:
            score += 25

        # Check for actionable language
        if len(words) >= 3:
            score += 25

        return {
            'valid': len(feedback) == 0,
            'score': min(score, 100),
            'feedback': feedback
        }

    def check_independence(self, items: List[str]) -> Tuple[bool, List[dict]]:
        """
        Check if all items are independent from each other.

        Returns:
            Tuple of (all_independent, list of similarity issues)
        """
        if len(items) < 2:
            return True, []

        # Create a fresh vectorizer per call to avoid thread-safety issues
        # (the shared self.vectorizer is mutated by fit_transform)
        try:
            vectorizer = TfidfVectorizer(
                stop_words='english', ngram_range=(1, 2), min_df=1
            )
            tfidf_matrix = vectorizer.fit_transform(items)
            similarity_matrix = cosine_similarity(tfidf_matrix)
        except Exception:
            # If vectorization fails, assume items are independent
            return True, []

        issues = []

        # Check each pair of items
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                similarity = similarity_matrix[i][j]
                if similarity > self.SIMILARITY_THRESHOLD:
                    issues.append({
                        'item1_index': i,
                        'item2_index': j,
                        'item1': items[i][:50] + "..." if len(items[i]) > 50 else items[i],
                        'item2': items[j][:50] + "..." if len(items[j]) > 50 else items[j],
                        'similarity': round(similarity * 100, 1),
                        'message': f"Items {i+1} and {j+1} are {round(similarity * 100)}% similar. Consider making them more distinct."
                    })

        return len(issues) == 0, issues

    def _validate_collection(self, items: List[str], item_label: str, min_required: int) -> dict:
        """Shared validation logic for pain/gain point collections."""
        results = {
            'valid': True,
            'count': len(items),
            'min_required': min_required,
            'enough_points': len(items) >= min_required,
            'individual_quality': [],
            'independence_check': None,
            'overall_feedback': []
        }

        # Check count
        if not results['enough_points']:
            results['valid'] = False
            results['overall_feedback'].append(
                f"You need at least {min_required} {item_label}s. Currently you have {len(items)}."
            )

        # Validate each point
        for i, point in enumerate(items):
            quality = self.validate_item_quality(point, item_label)
            quality['index'] = i
            results['individual_quality'].append(quality)
            if not quality['valid']:
                results['valid'] = False

        # Check independence
        if len(items) >= 2:
            independent, issues = self.check_independence(items)
            results['independence_check'] = {
                'independent': independent,
                'issues': issues
            }
            if not independent:
                results['valid'] = False
                results['overall_feedback'].append(
                    f"Some {item_label}s are too similar. Please ensure each {item_label} is unique and distinct."
                )

        return results

    def validate_pain_points(self, pain_points: List[str]) -> dict:
        """Validate all pain points for quality and independence."""
        return self._validate_collection(pain_points, "pain point", self.MIN_PAIN_POINTS)

    def validate_gain_points(self, gain_points: List[str]) -> dict:
        """Validate all gain points for quality and independence."""
        return self._validate_collection(gain_points, "gain point", self.MIN_GAIN_POINTS)

    def validate_complete_canvas(self, job_description: str, pain_points: List[str],
                                  gain_points: List[str]) -> dict:
        """
        Validate the complete canvas.
        """
        job_result = self.validate_job_description(job_description)
        pain_result = self.validate_pain_points(pain_points)
        gain_result = self.validate_gain_points(gain_points)

        overall_valid = (job_result['valid'] and pain_result['valid'] and gain_result['valid'])

        overall_score = (
            job_result['score'] * self.JOB_WEIGHT +
            (100 if pain_result['valid'] else 50) * self.PAIN_WEIGHT +
            (100 if gain_result['valid'] else 50) * self.GAIN_WEIGHT
        )

        return {
            'valid': overall_valid,
            'overall_score': round(overall_score),
            'job_description': job_result,
            'pain_points': pain_result,
            'gain_points': gain_result,
            'ready_for_export': overall_valid
        }

    def compute_priority_level(self, result: dict) -> str:
        """Determine the highest-priority feedback tier for progressive disclosure.

        Returns one of: 'count', 'quality', 'independence', 'complete'
        - 'count': not enough items yet (show count feedback only)
        - 'quality': enough items but quality issues exist
        - 'independence': quality OK but items are too similar
        - 'complete': everything passes
        """
        if not result.get('enough_points', True):
            return 'count'

        quality_issues = any(
            not q.get('valid', True)
            for q in result.get('individual_quality', [])
        )
        if quality_issues:
            return 'quality'

        independence = result.get('independence_check')
        if independence and not independence.get('independent', True):
            return 'independence'

        return 'complete'

    def compute_positive_feedback(self, result: dict, item_label: str) -> List[str]:
        """Generate positive feedback messages for items that pass validation."""
        feedback = []
        count = result.get('count', 0)
        min_required = result.get('min_required', 0)

        if count >= min_required:
            feedback.append(f"Great — you have {count} {item_label}s, meeting the minimum of {min_required}.")

        quality_scores = [q.get('score', 0) for q in result.get('individual_quality', [])]
        if quality_scores:
            avg_score = sum(quality_scores) / len(quality_scores)
            if avg_score >= 75:
                feedback.append(f"Good specificity across your {item_label}s.")

        independence = result.get('independence_check')
        if independence and independence.get('independent', True) and count >= 2:
            feedback.append(f"All {item_label}s are distinct from each other.")

        return feedback

    def classify_dimension(self, item: str) -> str:
        """Classify an item into functional/emotional/social dimension using keywords."""
        item_lower = item.lower()

        emotional_keywords = [
            'frustrat', 'stress', 'anxious', 'anxiety', 'worry', 'fear', 'annoy',
            'overwhelm', 'confus', 'embarrass', 'disappoint', 'satisf', 'happy',
            'enjoy', 'excit', 'confident', 'proud', 'relief', 'comfort', 'feel',
            'emotion', 'motivation', 'morale', 'burnout', 'exhaust',
        ]
        social_keywords = [
            'team', 'collaborat', 'communicat', 'reputation', 'trust', 'recogni',
            'respect', 'relationship', 'stakeholder', 'colleague', 'manager',
            'client', 'customer', 'peer', 'network', 'community', 'status',
            'credibility', 'influence', 'feedback from', 'approval',
        ]

        emotional_score = sum(1 for kw in emotional_keywords if kw in item_lower)
        social_score = sum(1 for kw in social_keywords if kw in item_lower)

        if emotional_score > social_score and emotional_score > 0:
            return 'emotional'
        elif social_score > emotional_score and social_score > 0:
            return 'social'
        elif emotional_score > 0 and social_score > 0:
            return 'emotional'  # tie-break to emotional
        else:
            return 'functional'  # default: if no emotional/social keywords, it's functional

    def _keyword_overlap_score(self, text1: str, text2: str) -> float:
        """Expand both texts using SYNONYM_CLUSTERS, then compute Jaccard similarity."""
        t1_lower = text1.lower()
        t2_lower = text2.lower()

        # Collect base words (non-stopword)
        set1 = {w.strip('.,;:!?') for w in t1_lower.split()} - self.STOPWORDS
        set2 = {w.strip('.,;:!?') for w in t2_lower.split()} - self.STOPWORDS

        # Expand via synonym clusters (substring match)
        expanded1 = set(set1)
        expanded2 = set(set2)
        for cluster in self.SYNONYM_CLUSTERS:
            t1_hit = any(term in t1_lower for term in cluster)
            t2_hit = any(term in t2_lower for term in cluster)
            if t1_hit:
                expanded1.update(cluster)
            if t2_hit:
                expanded2.update(cluster)

        if not expanded1 or not expanded2:
            return 0.0
        intersection = expanded1 & expanded2
        union = expanded1 | expanded2
        return len(intersection) / len(union) if union else 0.0

    def _jaccard_stem_score(self, text1: str, text2: str, stem_len: int = 6) -> float:
        """Crude stemming (truncate to stem_len), then Jaccard on stem sets."""
        def stems(text: str) -> set:
            words = {w.strip('.,;:!?') for w in text.lower().split()} - self.STOPWORDS
            return {w[:stem_len] for w in words if len(w) > 2}

        s1 = stems(text1)
        s2 = stems(text2)
        if not s1 or not s2:
            return 0.0
        intersection = s1 & s2
        union = s1 | s2
        return len(intersection) / len(union) if union else 0.0

    def check_relevance(self, items: List[str], job_description: str) -> dict:
        """Check if items are relevant to the job description using hybrid scoring.

        Combines TF-IDF cosine similarity, synonym-expanded keyword overlap,
        and Jaccard stem similarity for robust relevance detection.
        """
        if not items or not job_description.strip():
            return {
                'relevant': True,
                'item_scores': [],
                'dimension_distribution': {'functional': 0, 'emotional': 0, 'social': 0},
            }

        RELEVANCE_THRESHOLD = 0.05

        try:
            vectorizer = TfidfVectorizer(
                stop_words='english', ngram_range=(1, 2), min_df=1
            )
            all_texts = [job_description] + list(items)
            tfidf_matrix = vectorizer.fit_transform(all_texts)

            job_vector = tfidf_matrix[0:1]
            item_vectors = tfidf_matrix[1:]
            similarities = cosine_similarity(item_vectors, job_vector).flatten()
        except Exception:
            similarities = np.zeros(len(items))

        item_scores = []
        all_relevant = True
        for i, item in enumerate(items):
            tfidf_score = float(similarities[i])
            kw_score = self._keyword_overlap_score(job_description, item)
            jac_score = self._jaccard_stem_score(job_description, item)
            combined = 0.4 * kw_score + 0.3 * jac_score + 0.3 * tfidf_score
            final_score = max(tfidf_score, combined)  # any strong signal passes

            score_pct = round(final_score * 100, 1)
            is_relevant = bool(final_score >= RELEVANCE_THRESHOLD)
            dimension = self.classify_dimension(item)

            entry = {
                'index': i,
                'item': item[:80] + '...' if len(item) > 80 else item,
                'relevance_score': score_pct,
                'relevant': is_relevant,
                'dimension': dimension,
            }
            if not is_relevant:
                entry['feedback'] = (
                    "This item may not be related to your job description. "
                    "Consider revising it to connect more clearly to your stated goal."
                )
                all_relevant = False

            item_scores.append(entry)

        return {
            'relevant': all_relevant,
            'item_scores': item_scores,
            'dimension_distribution': self._count_dimensions(items),
        }

    def _count_dimensions(self, items: List[str]) -> dict:
        """Count items per dimension."""
        dist = {'functional': 0, 'emotional': 0, 'social': 0}
        for item in items:
            dim = self.classify_dimension(item)
            dist[dim] = dist.get(dim, 0) + 1
        return dist