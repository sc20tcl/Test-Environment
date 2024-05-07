import http from 'k6/http';
import { sleep } from 'k6';

export let options = {
    vus: 1, 
    duration: '60s', 
    noVUConnectionReuse: false,
};

const urls = [
    'http://4.158.24.106:8080/tools.descartes.teastore.webui/category?category=2&page=1',
    'http://4.158.24.106:8080/tools.descartes.teastore.webui/category?category=3&page=1',
    'http://4.158.24.106:8080/tools.descartes.teastore.webui/category?category=4&page=1',
    'http://4.158.24.106:8080/tools.descartes.teastore.webui/product?id=207',
    'http://4.158.24.106:8080/tools.descartes.teastore.webui/category?category=6&page=1'
];

export default function () {
    const url = urls[Math.floor(Math.random() * urls.length)];

    http.get(url);
    sleep(1);
}