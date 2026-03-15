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
    SIMILARITY_THRESHOLD = 0.7

    # Minimum requirements
    MIN_PAIN_POINTS = 7
    MIN_GAIN_POINTS = 8

    # Vague-word ratio threshold for specificity check
    VAGUE_WORD_RATIO = 0.2

    # Overall canvas score weighting (must sum to 1.0)
    JOB_WEIGHT = 0.30
    PAIN_WEIGHT = 0.35
    GAIN_WEIGHT = 0.35

    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            stop_words='english',
            ngram_range=(1, 2),
            min_df=1
        )

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