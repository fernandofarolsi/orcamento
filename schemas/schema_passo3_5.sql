-- Add flag to distinguish accessories
ALTER TABLE estoque ADD COLUMN is_acessorio BOOLEAN DEFAULT 0;
