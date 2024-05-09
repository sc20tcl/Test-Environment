import http from 'k6/http';

let rate = __ENV.RATE || '100';  
let duration = __ENV.DURATION || '1m'; 
let preAllocatedVUs = __ENV.PREALLOCATED_VUS || '20';  
let maxVUs = __ENV.MAX_VUS || '100';  

export const options = {
    scenarios: {
        constant_request_rate: {
            executor: 'constant-arrival-rate',
            rate: parseInt(rate),  
            timeUnit: '1s', 
            duration: duration,
            preAllocatedVUs: parseInt(preAllocatedVUs),  
            maxVUs: parseInt(maxVUs),  
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
