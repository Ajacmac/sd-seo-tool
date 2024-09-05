import logging
from typing import Any, Dict, List

import networkx as nx
import numpy as np
from networkx.algorithms import community
from scipy.cluster.hierarchy import fcluster, linkage
from sentence_transformers import SentenceTransformer


class EmbeddingService:
    def __init__(
        self, model_name: str = "TaylorAI/bge-micro-v2", cache_size: int = 10000
    ):
        """
        TODO: Figure out if the cache_size affects memory usage
        """
        self.model = SentenceTransformer(model_name)
        self.cache: Dict[str, np.ndarray] = {}
        self.cache_size = cache_size
        logging.info(f"Initialized EmbeddingService with model: {model_name}")

    def get_embedding(self, text: str) -> np.ndarray:
        if text in self.cache:
            return self.cache[text]

        embedding = self.model.encode(text, convert_to_numpy=True)

        if len(self.cache) >= self.cache_size:
            self.cache.pop(next(iter(self.cache)))

        self.cache[text] = embedding
        return embedding

    def get_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        return [self.get_embedding(text) for text in texts]

    def cosine_similarity(self, text1: str, text2: str) -> float:
        emb1 = self.get_embedding(text1)
        emb2 = self.get_embedding(text2)
        return np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))

    def cosine_from_embedding(self, emb1: float, emb2: float) -> float:
        return np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))

    def euclidean_distance(self, text1: str, text2: str) -> float:
        emb1 = self.get_embedding(text1)
        emb2 = self.get_embedding(text2)
        return np.linalg.norm(emb1 - emb2)

    def find_similar_keywords(
        self, seed_keyword: str, potential_keywords: List[str], threshold: float = 0.5
    ) -> List[str]:
        seed_emb = self.get_embedding(seed_keyword)
        similar_keywords = []

        for keyword in potential_keywords:
            key_emb = self.get_embedding(keyword)
            similarity = self.cosine_from_embedding(seed_emb, key_emb)
            if similarity >= threshold:
                similar_keywords.append(keyword)

        return similar_keywords

    def bucket_cosine(
        self, center: Any, keywords: List[str], center_type: str, buckets: int = 100
    ) -> Dict[str, Any]:
        """
        Bucket keywords from the list by their cosine similarity to the keyword string.
        Uses cosine similarity and euclidean distance to determine similarity.

        Returns a dictionary with keys representing the bucket range and values
        being lists of keywords that fall within that range

        center - The embedding point to compare the keywords to (can be a keyword or an embedding)
        keywords - The list of keyword strings to compare to center
        center_type - The type of center to compare to, either "keyword" or "embedding"

        Bucket sizes are calculated based on the number of buckets specified out
        of a range from -1 to 1, with higher being more similar

        FIXME: Should this take a pair of lists?
            - List of seed keywords
            - List of potential keywords

        Should I be bucketing based on averages?

        TODO: Test euclidean distance on its own
        TODO: Compare to cosine similarity

        TODO: Test normalizing then averaging the scores
        TODO: Test comparing to individual seed keywords
        TODO: Test comparing to the average embedding of all seed keywords

        Additional comparison targets for candidate keywords:
            - Client website
            - Client website + keywords (may be redundant since keywords *should* be on the website)
            - Client description
            - Client service list
            - Individual client service descriptions
            - Different kinds of embedding vector averages


        Later:
        TODO: Test different embedding models
        """

        if center_type == "keyword":
            seed_emb = self.get_embedding(center)
        elif center_type == "embedding":
            seed_emb = center
        else:
            raise ValueError("center_type must be 'keyword' or 'embedding'")

        min = -1
        max = 1
        bucket_size = (max - min) / buckets
        bucketed_keywords = {str(min + (i * bucket_size)): [] for i in range(buckets)}

        for kw in keywords:
            keyword_emb = self.get_embedding(kw)
            similarity = self.cosine_from_embedding(seed_emb, keyword_emb)

            for bucket in bucketed_keywords:
                if (
                    similarity >= float(bucket)
                    and similarity < float(bucket) + bucket_size
                ):
                    bucketed_keywords[bucket].append(kw)
                    break

        return bucketed_keywords

    def bucket_euclidean(
        self, keyword: str, keywords: List[str], buckets: int = 100
    ) -> Dict[str, Any]:
        """
        Bucket keywords from the list by their euclidean distance to the keyword string.

        Returns a dictionary with keys representing the bucket range and values
        being lists of keywords that fall within that range

        Bucket sizes are calculated based on the number of buckets specified out
        of a range from 0 to 1

        FIXME: verify this works
        """

        min = -1
        max = 1
        bucket_size = (max - min) / buckets
        bucketed_keywords = {str(min + (i * bucket_size)): [] for i in range(buckets)}

        seed_emb = self.get_embedding(keyword)

        for kw in keywords:
            keyword_emb = self.get_embedding(kw)
            similarity = self.cosine_from_embedding(seed_emb, keyword_emb)

            for bucket in bucketed_keywords:
                if (
                    similarity >= float(bucket)
                    and similarity < float(bucket) + bucket_size
                ):
                    bucketed_keywords[bucket].append(kw)
                    break

        return bucketed_keywords

    def bucket_weighted(
        self, keyword: str, keywords: List[str], buckets: int = 100
    ) -> Dict[str, Any]:
        """
        Bucket keywords from the list by their normalized and weighted similarity to the keyword string.
        Uses cosine similarity and euclidean distance to determine similarity.

        Returns a dictionary with keys representing the bucket range and values
        being lists of keywords that fall within that range

        Bucket sizes are calculated based on the number of buckets specified out
        of a range from -1 to 1, with higher being more similar

        FIXME: implement this
        """

    def assign_to_cluster(self, new_keyword, seed_keywords):
        """
        FIXME: Verify this works
        """

        max_similarity = -1
        assigned_cluster = None
        for seed in seed_keywords:
            cos_sim = self.cosine_similarity(new_keyword, seed)
            euc_dist = self.euclidean_distance(new_keyword, seed)
            combined_sim = self.combine_scores(
                cos_sim, euc_dist
            )  # FIXME: implement this
            if combined_sim > max_similarity:
                max_similarity = combined_sim
                assigned_cluster = seed
        return assigned_cluster

    def categorize_keyword(self, new_keyword, seed_keywords, threshold=0.7):
        """
        FIXME: verify this works
        """

        categories = []
        for seed in seed_keywords:
            cos_sim = self.cosine_similarity(new_keyword, seed)
            if cos_sim >= threshold:
                categories.append(seed)
        return categories

    def hierarchical_clustering(self, keywords, n_clusters):
        """
        Seems to work, at least in principle

        FIXME: hierarchical clustering doesn't seem to be able to
        help with grouping informational keywords together by the
        information they're after
        - I need to figure out how to do that

        Should I make the fcluster call more directly configurable from
        the arguments to this function?

        """

        embeddings = [self.get_embedding(kw) for kw in keywords]
        linkage_matrix = linkage(embeddings, method="ward")
        clusters = fcluster(linkage_matrix, n_clusters, criterion="maxclust")
        return {
            i: [kw for j, kw in enumerate(keywords) if clusters[j] == i]
            for i in range(1, n_clusters + 1)
        }

    def combine_scores(self, cos_sim, euc_dist):
        """
        Combine cosine similarity and euclidean distance scores into a single score

        FIXME: implement this
        """

    def create_similarity_network(self, keywords, threshold=0.7):
        """
        FIXME: Verify this works
        """

        G = nx.Graph()
        for i, kw1 in enumerate(keywords):
            for j, kw2 in enumerate(keywords[i + 1 :], i + 1):
                sim = self.cosine_similarity(kw1, kw2)
                if sim >= threshold:
                    G.add_edge(kw1, kw2, weight=sim)
        return G

    def detect_communities(G):
        return list(community.greedy_modularity_communities(G))

    def get_centroid(self, keywords):
        """
        Get the centroid of a group of keywords using the mean of their embeddings
        """
        embeddings = [self.get_embedding(kw) for kw in keywords]
        return np.mean(embeddings, axis=0)


embedding_service = EmbeddingService()  # Global instance
logging.info("EmbeddingService instantiated successfully")

__all__ = ["embedding_service"]
