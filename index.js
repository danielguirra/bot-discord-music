import express from 'express'
const app = express();
const port = 3000;
import {PythonShell} from 'python-shell';
let pyshell = new PythonShell('main.py');
app.get('/', (req, res) => res.send('Servidor online!'));

app.listen(port, () => console.log(`O bot está rodando na porta: http://localhost:${port}`));