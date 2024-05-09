import http from 'k6/http';

export const options = {
    scenarios: {
        constant_request_rate: {
            executor: 'constant-arrival-rate',
            rate: 100,  
            timeUnit: '1s',  
            duration: '10m',  
            preAllocatedVUs: 50, 
            maxVUs: 200,  
        }
    }
};


const urls = [
    'http://4.158.24.106:8080/tools.descartes.teastore.webui/category?category=2&page=1',
    'http://4.158.24.106:8080/tools.descartes.teastore.webui/category?category=3&page=1',
    'http://4.158.24.106:8080/tools.descartes.teastore.webui/category?category=4&page=1',
    'http://4.158.24.106:8080/tools.descartes.teastore.webui/product?id=207',
    'http://4.158.24.106:8080/tools.descartes.teastore.webui/category?category=6&page=1'
];

export default function () {
    http.get(urls[Math.floor(Math.random() * urls.length)]);
}
