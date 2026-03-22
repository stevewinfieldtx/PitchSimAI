const API_BASE = '/api';

class ApiClient {
  async request(path, options = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || 'Request failed');
    }

    if (response.status === 204) return null;
    return response.json();
  }

  // Simulations
  async createSimulation(data) {
    return this.request('/simulations', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async listSimulations(params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.request(`/simulations${query ? '?' + query : ''}`);
  }

  async getSimulation(id) {
    return this.request(`/simulations/${id}`);
  }

  async getSimulationResponses(id) {
    return this.request(`/simulations/${id}/responses`);
  }

  // Personas
  async listPersonas(params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.request(`/personas${query ? '?' + query : ''}`);
  }

  async createPersona(data) {
    return this.request('/personas', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updatePersona(id, data) {
    return this.request(`/personas/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deletePersona(id) {
    return this.request(`/personas/${id}`, { method: 'DELETE' });
  }

  async getIndustries() {
    return this.request('/personas/industries/list');
  }

  // Chat
  async sendChatMessage(simulationId, personaId, message) {
    return this.request(`/chat/${simulationId}/${personaId}`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
  }

  async getChatHistory(simulationId, personaId) {
    return this.request(`/chat/${simulationId}/${personaId}/history`);
  }

  // Buying Committee
  async generateCommittee(data) {
    return this.request('/committee/generate', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async generateSinglePersona(data) {
    return this.request('/committee/generate-persona', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async enrichFromLinkedIn(data) {
    return this.request('/committee/enrich/linkedin', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async enrichFromName(data) {
    return this.request('/committee/enrich/name', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getWarmthOptions() {
    return this.request('/committee/warmth-options');
  }

  async getSupportedIndustries() {
    return this.request('/committee/industries');
  }

  // Health & Engine Status
  async healthCheck() {
    return this.request('/health/full');
  }

  async getModelStats() {
    return this.request('/models/stats');
  }

  async getModelPool() {
    return this.request('/models/pool');
  }
}

export const api = new ApiClient();
