import sys
with open("frontend/src/components/Ingest.jsx", "r") as f:
    content = f.read()

# Remove domain state
content = content.replace("const [domain, setDomain] = useState('');", "")
content = content.replace("const data = await ingestData(domain, file);", "const data = await ingestData(file);")
content = content.replace("setDomain('');", "")

# Remove dropdown block
dropdown_block = """        <div className="input-group">
          <label>Target Namespace / Domain</label>
          <select
            className="input-field"
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            required
          >
            <option value="" disabled>Select Domain</option>
            <option value="IT">IT</option>
            <option value="HR">HR</option>
          </select>
        </div>"""
content = content.replace(dropdown_block, "")

# Remove domain references from imports/state if any other exist (handled)

with open("frontend/src/components/Ingest.jsx", "w") as f:
    f.write(content)
