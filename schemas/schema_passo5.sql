-- Sem mudanças de schema necessárias pois 'site_origem' já existe.
-- Inserindo alguns itens de exemplo para serem "atualizados" pelo raspador.

INSERT INTO estoque (nome, categoria, unidade, quantidade, custo_unitario, site_origem) VALUES
('MDF Branco 15mm (TESTE)', 'MDF', 'chapa', 10, 100.00, 'madeiranit'),
('Sarrafo Pinus (TESTE)', 'Madeira', 'm', 50, 5.00, 'madeverde');
