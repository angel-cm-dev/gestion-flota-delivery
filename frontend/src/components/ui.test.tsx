import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AsyncContent, Pagination, StatusBadge } from './ui';

describe('Pagination', () => {
  it('muestra el total y deshabilita "anterior" en la primera página', async () => {
    const onPage = vi.fn();
    render(<Pagination page={1} pages={3} total={25} onPage={onPage} />);
    expect(screen.getByText(/25 registros · página 1 de 3/)).toBeInTheDocument();
    expect(screen.getByLabelText('Página anterior')).toBeDisabled();
    await userEvent.click(screen.getByLabelText('Página siguiente'));
    expect(onPage).toHaveBeenCalledWith(2);
  });

  it('no se muestra si no hay registros', () => {
    const { container } = render(<Pagination page={1} pages={0} total={0} onPage={() => {}} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe('StatusBadge', () => {
  it('traduce el estado a una etiqueta legible', () => {
    render(<StatusBadge status="en_ruta" />);
    expect(screen.getByText('En ruta')).toBeInTheDocument();
  });
});

describe('AsyncContent', () => {
  it('muestra carga, error con reintento, vacío y contenido', async () => {
    const retry = vi.fn();
    const { rerender } = render(<AsyncContent loading error={null}>ok</AsyncContent>);
    expect(screen.getByRole('status')).toHaveTextContent('Cargando');

    rerender(<AsyncContent loading={false} error="Falló" onRetry={retry}>ok</AsyncContent>);
    expect(screen.getByRole('alert')).toHaveTextContent('Falló');
    await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }));
    expect(retry).toHaveBeenCalled();

    rerender(<AsyncContent loading={false} error={null} empty emptyTitle="Nada aquí">ok</AsyncContent>);
    expect(screen.getByText('Nada aquí')).toBeInTheDocument();

    rerender(<AsyncContent loading={false} error={null}>contenido</AsyncContent>);
    expect(screen.getByText('contenido')).toBeInTheDocument();
  });
});
