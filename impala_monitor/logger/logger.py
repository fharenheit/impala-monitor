import concurrent.futures
import requests

from elasticsearch import Elasticsearch
from lru import LRU

from .parser import Query
from .parser import ImpalaQueryLogParser


class ElasticFactory(object):
    def __init__(self, host: str, port: str):
        self.port = port
        self.host = host

    def create(self) -> Elasticsearch:
        return Elasticsearch(
            [{'host': self.host, 'port': self.port}]
        )


class ImpalaLogger(object):
    def __init__(
            self,
            nodes: list,
            elastic_host: str,
            elastic_port: int,
            lru_size: int = 5000
    ):
        self.elastic_port = elastic_port
        self.elastic_host = elastic_host
        self.nodes = nodes
        self.queries_logged = LRU(lru_size)
        self.elasticsearch = ElasticFactory(
            self.elastic_host, self.elastic_port
        ).create()

    def run(self):
        """
        We need to get from all the nodes the required information.
        In this case we need to first of all load the queries, and then the
        metadata on the query profile.

        :return:
        """
        queries = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(self.query_retriever, node, 2): node for node
                in
                self.nodes
            }

            for future in concurrent.futures.as_completed(futures):
                node = futures[future]
                try:
                    retrieved_queries = future.result()

                    for query in retrieved_queries:
                        if not self.queries_logged.has_key(query.query_id):
                            self.queries_logged[query.query_id] = True
                            query.node = node
                            queries.append(query)

                except Exception as e:
                    print("Something went wrong {}".format(e))

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(self.query_profiler, query, 2): query for
                query in queries
            }

            for future in concurrent.futures.as_completed(futures):
                try:
                    query = future.result()

                    # send to elastic
                    self.elasticsearch.index(
                        index='query_log', doc_type='query', id=query.query_id,
                        body=query.to_dict()
                    )

                except Exception as e:
                    print('Something went wrong {}'.format(e))

    @staticmethod
    def query_retriever(node: str, timeout: int = 1) -> list:
        url = "{schema}{ip}/{path}".format(
            schema='http://',
            ip=node,
            path='queries'
        )

        request = requests.get(url, timeout=timeout)
        if request.status_code != 200:
            return False

        parser = ImpalaQueryLogParser(request.text)
        queries = parser.queries

        if not queries:
            return []

        return queries

    @staticmethod
    def query_profiler(query: Query, timeout: int = 1) -> Query:
        url = "{schema}{ip}/query_profile?query_id={query_id}".format(
            schema='http://',
            ip=query.node,
            query_id=query.query_id
        )

        request = requests.get(url, timeout=timeout)
        if request.status_code != 200:
            return False

        return ImpalaQueryLogParser(request.text).extract_profile(query)
