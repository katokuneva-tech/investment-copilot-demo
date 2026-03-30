'use client';

import { useState, useEffect, useCallback } from 'react';
import { KBDocument } from '@/lib/types';
import { fetchDocuments, uploadDocument, deleteDocument, toggleDocument } from '@/lib/api';

export function useDocuments() {
  const [documents, setDocuments] = useState<KBDocument[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    try {
      const docs = await fetchDocuments();
      setDocuments(docs);
    } catch (err) {
      console.error('Failed to fetch documents:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const upload = useCallback(async (file: File) => {
    try {
      await uploadDocument(file);
      await refresh();
    } catch (err) {
      console.error('Failed to upload:', err);
    }
  }, [refresh]);

  const remove = useCallback(async (docId: string) => {
    try {
      await deleteDocument(docId);
      await refresh();
    } catch (err) {
      console.error('Failed to delete:', err);
    }
  }, [refresh]);

  const toggle = useCallback(async (docId: string) => {
    try {
      const updated = await toggleDocument(docId);
      setDocuments(prev => prev.map(d => d.id === docId ? updated : d));
    } catch (err) {
      console.error('Failed to toggle document:', err);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { documents, isLoading, upload, remove, toggle, refresh };
}
