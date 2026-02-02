import unittest
import sys
from unittest.mock import MagicMock, patch

# Mock dependencies before import
sys.modules["openai"] = MagicMock()
sys.modules["neo4j"] = MagicMock()

from src.retrieval.graph import Neo4jGraphRetriever

class TestCompleteGraphRAG(unittest.TestCase):
    def setUp(self):
        self.mock_driver = MagicMock()
        self.mock_session = MagicMock()
        self.mock_driver.session.return_value.__enter__.return_value = self.mock_session
        
        # Patch the client getter
        self.patcher = patch('src.database.neo4j.client.get_neo4j_driver', return_value=self.mock_driver)
        self.patcher.start()
        
        # Patch config getter
        self.config_patcher = patch('src.config.get_openai_client')
        self.mock_openai = self.config_patcher.start()
        
        # Setup embedding mock
        self.mock_embedding_response = MagicMock()
        self.mock_embedding_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
        self.mock_openai.embeddings.create.return_value = self.mock_embedding_response

        self.retriever = Neo4jGraphRetriever()

    def tearDown(self):
        self.patcher.stop()
        self.config_patcher.stop()

    def test_full_rag_flow(self):
        """Test the complete retrieval flow: Vector -> Expansion -> Chunks"""
        
        # 1. Mock Vector Search Result
        vector_result = [{
            'entity_name': 'Section 420',
            'entity_type': 'Section',
            'source': 'IPC.pdf',
            'score': 0.95
        }]
        
        # 2. Mock Expansion Result (Semantic + Hierarchy)
        expansion_result = {
            'expanded_data': {
                'entity': 'Section 420',
                'type': 'Section',
                'semantic_connections': [{'neighbor': 'Cheating', 'rel_type': 'PENALIZES'}],
                'hierarchy': [['Chapter XVII', 'IPC']]
            }
        }
        
        # 3. Mock Chunk Result
        chunk_result = [
            {'text': 'Whoever cheats...', 'source': 'IPC.pdf', 'chunk_id': 1}
        ]
        
        # Configure side_effect to return different results for sequential calls
        # Call 1: Vector Search
        # Call 2: Expansion
        # Call 3: Chunk Fetch
        
        # Since session.run is termed multiple times, we need to mock based on query content or sequence
        # Simplified: We use a side_effect function
        def run_side_effect(query, **kwargs):
            mock_result = MagicMock()
            if "db.index.vector.queryNodes" in query:
                mock_result.data.return_value = vector_result
                return mock_result
            elif "semantic_rels" in query: # Identified key in expansion query
                mock_result.single.return_value = expansion_result
                return mock_result
            elif "MENTIONED_IN" in query:
                mock_result.data.return_value = chunk_result
                return mock_result
            return mock_result

        self.mock_session.run.side_effect = run_side_effect

        # Act
        result = self.retriever.retrieve(
            query="fraud",
            include_chunks=True,
            source_filter="IPC",
            resolution_depth=2
        )

        # Assert
        self.assertEqual(len(result.results), 1)
        self.assertEqual(result.results[0]['entity'], 'Section 420')
        self.assertEqual(result.results[0]['chunks'][0]['text'], 'Whoever cheats...')
        self.assertEqual(result.results[0]['hierarchy'], [['Chapter XVII', 'IPC']])
        
        # Verify Source Filter was applied in Vector Query
        vector_call_args = self.mock_session.run.call_args_list[0]
        self.assertIn("node.source CONTAINS 'IPC'", vector_call_args[0][0])
        
        print("\nTest Full RAG Flow: SUCCESS")

    def test_adaptive_traversal_logic(self):
        """Verify that correct structural types are used in query"""
        
        def run_side_effect(query, **kwargs):
            mock_result = MagicMock()
            if "semantic_rels" in query:
                # This is the expansion query - check it!
                self.assertIn("PART_OF|CONTAINS|CHAPTER_IN|SECTION_IN", query)
                self.assertIn("CASE WHEN startNode(r) = e", query) # Bidirectional check
                mock_result.single.return_value = {'expanded_data': {}}
            return mock_result
            
        self.mock_session.run.side_effect = run_side_effect
        
        self.retriever.expand_entity_neighbors("test_entity")
        print("\nTest Adaptive Traversal Logic: SUCCESS")

if __name__ == '__main__':
    unittest.main()
